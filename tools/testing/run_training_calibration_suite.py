#!/usr/bin/env python
"""
run_training_calibration_suite.py — TASK-079
Orchestrateur : simulation adaptative + calibrations moteur + régression → rapport markdown.

Usage:
  python tools/testing/run_training_calibration_suite.py --user Guilhem --quick
  python tools/testing/run_training_calibration_suite.py --user Guilhem --full
  python tools/testing/run_training_calibration_suite.py --user Guilhem --n 30
  python tools/testing/run_training_calibration_suite.py --user Guilhem --mode api --skip-api-confirm

Modes:
  --quick  : simulation mock n=20, calibrations, pas de régression
  --full   : simulation mock n=50, calibrations complètes, régression, rapport markdown
  (défaut) : --full implicite avec n=50
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Encodage Windows ──────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SEP  = "─" * 72
SEP2 = "━" * 72

_MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Training & Calibration Suite — ADDISCO OPS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--user",             default="Guilhem",
                   help="Nom d'utilisateur pour la simulation (défaut: Guilhem)")
    p.add_argument("--n",                type=int, default=50,
                   help="Nombre d'attempts simulés (défaut: 50)")
    p.add_argument("--mode",             default="mock", choices=["mock", "api"],
                   help="Mode simulation : mock (défaut) ou api")
    p.add_argument("--skip-api-confirm", action="store_true",
                   help="Désactive la confirmation pour le mode API (requis avec --mode api)")
    p.add_argument("--quick",            action="store_true",
                   help="Mode rapide : n=20, sans régression")
    p.add_argument("--full",             action="store_true",
                   help="Mode complet : n=50, régression, rapport markdown")
    p.add_argument("--no-regression",    action="store_true",
                   help="Sauter les tests de régression")
    p.add_argument("--output",           default=None,
                   help="Fichier rapport .md (défaut: reports/training_calibration_YYYYMMDD_HHMM.md)")
    return p.parse_args()


def _resolve_config(args: argparse.Namespace) -> dict:
    """Résout les options finales selon les flags --quick / --full."""
    n    = args.n
    mode = args.mode
    run_regression = not args.no_regression

    if args.quick:
        n              = min(n, 20)
        run_regression = False

    if args.full:
        n              = max(n, 50)
        run_regression = True

    _ts = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = args.output or str(ROOT / "reports" / f"training_calibration_{_ts}.md")

    return {
        "user":           args.user,
        "n":              n,
        "mode":           mode,
        "skip_confirm":   args.skip_api_confirm,
        "run_regression": run_regression,
        "quick":          args.quick,
        "full":           args.full or (not args.quick),
        "output_path":    output_path,
        "ts":             _ts,
    }


# ── Subprocess wrapper ────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 180) -> tuple[int, str, str]:
    """Exécute une commande, retourne (returncode, stdout, stderr)."""
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(ROOT),
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT après {timeout}s"
    except Exception as exc:
        return -2, "", str(exc)


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_simulation(stdout: str, n: int) -> dict:
    """Extrait les métriques structurées du bloc COPY_FOR_ANALYSIS."""
    data: dict = {
        "verdict":   "UNKNOWN",
        "n_saved":   None,
        "n_total":   n,
        "d_score":   None,
        "fb_pct":    None,
        "align_pct": None,
        "cost":      None,
        "avg_lat":   None,
        "non_ev":    None,
        "avg_score_after": None,
        "error_types": {},
    }

    start = stdout.find("=== COPY_FOR_ANALYSIS_START ===")
    end   = stdout.find("=== COPY_FOR_ANALYSIS_END ===")
    if start == -1:
        return data

    block = stdout[start:end] if end != -1 else stdout[start:]

    def _re(pattern: str):
        m = re.search(pattern, block)
        return m if m else None

    m = _re(r"- Verdict\s*:\s*\*\*(\w+)\*\*")
    if m:
        data["verdict"] = m.group(1)

    m = _re(r"- Saved\s*:\s*(\d+)/(\d+)")
    if m:
        data["n_saved"] = int(m.group(1))
        data["n_total"] = int(m.group(2))

    m = _re(r"- Score\s*:\s*([+-]?\d+\.\d+)")
    if m:
        data["d_score"] = float(m.group(1))

    m = _re(r"- Fallback\s*:\s*([\d.]+)%")
    if m:
        data["fb_pct"] = float(m.group(1))

    m = _re(r"- Alignment\s*:\s*([\d.]+)%")
    if m:
        data["align_pct"] = float(m.group(1))

    m = _re(r"- Coût\s*:\s*\$([\d.]+)")
    if m:
        data["cost"] = float(m.group(1))

    m = _re(r"- Latence moy\s*:\s*(\d+)\s*ms")
    if m:
        data["avg_lat"] = int(m.group(1))

    m = _re(r"- non_evaluable\s*:\s*(\d+)")
    if m:
        data["non_ev"] = int(m.group(1))

    # État APRÈS — score moyen
    m = _re(r"## État APRÈS\s*\n- Score moyen\s*:\s*([\d.]+)")
    if m:
        data["avg_score_after"] = float(m.group(1))

    # Distribution error_type
    for _m in re.finditer(r"^- (\w+): (\d+)$", block, re.MULTILINE):
        key, cnt = _m.group(1), int(_m.group(2))
        if key not in ("Score", "Saved", "Fallback", "Alignment"):
            data["error_types"][key] = cnt

    return data


def _parse_calib(
    stdout: str,
    rc: int,
    key_strings: list[str],
    name: str,
) -> dict:
    """Vérifie qu'un script de calibration a produit les marqueurs attendus."""
    missing = [s for s in key_strings if s not in stdout]
    ok = (rc == 0) and (len(missing) == 0)
    return {
        "name":       name,
        "ok":         ok,
        "rc":         rc,
        "missing":    missing,
        "stdout_tail": stdout[-800:].strip() if stdout else "",
    }


def _parse_regression(stdout: str, stderr: str) -> dict:
    combined = stdout + stderr
    m = re.search(r"Ran (\d+) tests in ([\d.]+)s", combined)
    n_tests = int(m.group(1)) if m else 0
    elapsed = float(m.group(2)) if m else 0.0
    ok = "OK" in combined.splitlines()[-2:]  # check last 2 lines
    # More robust: last non-empty line
    last_lines = [l for l in combined.splitlines() if l.strip()]
    ok = any(l.strip() == "OK" for l in last_lines[-3:])
    detail = ""
    for line in last_lines:
        if "FAILED" in line or "ERROR" in line:
            detail = line.strip()
            break
    return {
        "ok":      ok,
        "n_tests": n_tests,
        "elapsed": elapsed,
        "detail":  detail,
    }


# ── Verdict global ────────────────────────────────────────────────────────────

def _compute_verdict(
    sim: dict,
    calips: list[dict],
    reg: dict | None,
    n: int,
) -> tuple[str, list[str], list[str]]:
    """Retourne (verdict, fails, warnings)."""
    fails: list[str] = []
    warnings: list[str] = []

    # ── Simulation ───────────────────────────────────────────────────────────
    if sim.get("n_saved") is not None:
        if sim["n_saved"] == 0:
            fails.append("Simulation : aucun attempt sauvegardé")
        elif sim["n_saved"] < n * 0.5:
            fails.append(
                f"Simulation : trop peu d'attempts ({sim['n_saved']}/{n})"
            )
    if sim.get("verdict") == "FAILED":
        fails.append("Simulation : verdict FAILED")

    if sim.get("d_score") is not None and sim["d_score"] < -0.15:
        warnings.append(f"Simulation : score en forte baisse ({sim['d_score']:+.3f})")
    if sim.get("fb_pct") is not None and sim["fb_pct"] > 20:
        warnings.append(f"Simulation : fallback élevé ({sim['fb_pct']:.1f}%)")
    if sim.get("align_pct") is not None and sim["align_pct"] < 20:
        warnings.append(
            f"Simulation : curriculum alignment faible ({sim['align_pct']:.1f}%)"
        )
    if sim.get("verdict") == "WARNING":
        warnings.append("Simulation : verdict WARNING")

    # ── Calibrations ─────────────────────────────────────────────────────────
    for c in calips:
        if not c["ok"]:
            if c["rc"] != 0:
                fails.append(f"Calibration {c['name']} : crash (rc={c['rc']})")
            else:
                fails.append(
                    f"Calibration {c['name']} : marqueurs absents — "
                    + ", ".join(f'"{s}"' for s in c["missing"][:2])
                )

    # ── Régression ───────────────────────────────────────────────────────────
    if reg is not None and not reg["ok"]:
        fails.append(
            f"Tests régression : FAILED — {reg['detail'] or 'voir output'}"
        )

    if fails:
        return "FAILED", fails, warnings
    if warnings:
        return "WARNING", fails, warnings
    return "GO SAFE", fails, warnings


# ── Rapport markdown ──────────────────────────────────────────────────────────

def _build_report(
    cfg: dict,
    sim: dict,
    sim_stdout: str,
    calips: list[dict],
    reg: dict | None,
    verdict: str,
    fails: list[str],
    warnings: list[str],
    elapsed_total: float,
) -> str:
    _now = datetime.now()
    _date_str = f"{_now.day} {_MONTHS_FR[_now.month - 1]} {_now.year}"
    lines: list[str] = []

    def _h1(t: str) -> None:
        lines.append(f"# {t}")
        lines.append("")

    def _h2(t: str) -> None:
        lines.append(f"## {t}")
        lines.append("")

    def _h3(t: str) -> None:
        lines.append(f"### {t}")
        lines.append("")

    def _row(*cols) -> None:
        lines.append("| " + " | ".join(str(c) for c in cols) + " |")

    def _sep(*cols) -> None:
        lines.append("| " + " | ".join("---" for _ in cols) + " |")

    def _blank() -> None:
        lines.append("")

    # ── En-tête ───────────────────────────────────────────────────────────────
    _h1("Training & Calibration Suite — ADDISCO OPS")
    lines.append(f"> Généré le {_date_str} à {_now.strftime('%H:%M:%S')}")
    _blank()

    # Résumé exécutif
    _h2("1. Résumé exécutif")
    _row("Champ", "Valeur")
    _sep("—", "—")
    _row("Date", f"{_date_str} {_now.strftime('%H:%M')}")
    _row("Utilisateur", cfg["user"])
    _row("Mode simulation", cfg["mode"].upper())
    _row("Attempts simulés", cfg["n"])
    _row("Régression",
         "oui" if cfg["run_regression"] else "non (--no-regression ou --quick)")
    _row("Durée totale", f"{elapsed_total:.1f}s")
    _row("**Verdict global**", f"**{verdict}**")
    _blank()

    if verdict == "GO SAFE":
        lines.append(
            "> ✅ **GO SAFE** — Toutes les vérifications passent. "
            "Le moteur est stable et cohérent. Prêt pour tests humains."
        )
    elif verdict == "WARNING":
        lines.append(
            "> ⚠️ **WARNING** — Des signaux anormaux ont été détectés. "
            "Analyser avant de continuer."
        )
    else:
        lines.append(
            "> ❌ **FAILED** — Des erreurs bloquantes ont été détectées. "
            "Ne pas continuer sans correction."
        )
    _blank()

    if fails:
        _h3("Problèmes bloquants")
        for f in fails:
            lines.append(f"- ❌ {f}")
        _blank()

    if warnings:
        _h3("Avertissements")
        for w in warnings:
            lines.append(f"- ⚠️ {w}")
        _blank()

    # ── Simulation ────────────────────────────────────────────────────────────
    _h2("2. Résultats simulation")
    _row("Métrique", "Valeur", "Statut")
    _sep("—", "—", "—")
    _row("Attempts créées",
         f"{sim['n_saved']}/{sim['n_total']}" if sim["n_saved"] is not None else "—",
         "✅" if (sim.get("n_saved") or 0) > 0 else "❌")
    _row("Score moyen (après)",
         f"{sim['avg_score_after']:.3f}" if sim.get("avg_score_after") else "—", "")
    _row("Delta score",
         f"{sim['d_score']:+.3f}" if sim.get("d_score") is not None else "—",
         "✅" if (sim.get("d_score") or 0) >= -0.15 else "⚠️")
    _row("Fallback rate",
         f"{sim['fb_pct']:.1f}%" if sim.get("fb_pct") is not None else "—",
         "✅" if (sim.get("fb_pct") or 0) <= 20 else "⚠️")
    _row("Curriculum alignment",
         f"{sim['align_pct']:.1f}%" if sim.get("align_pct") is not None else "—",
         "✅" if (sim.get("align_pct") or 100) >= 20 else "⚠️")
    _row("Coût estimé",
         f"${sim['cost']:.6f}" if sim.get("cost") is not None else "n/a (mock)", "")
    _row("Latence moy.",
         f"{sim['avg_lat']} ms" if sim.get("avg_lat") is not None else "—", "")
    _row("Non évaluables",
         str(sim["non_ev"]) if sim.get("non_ev") is not None else "—", "")
    _row("Verdict simulation",
         sim["verdict"],
         "✅" if sim["verdict"] == "COHERENT" else ("⚠️" if sim["verdict"] == "WARNING" else "❌"))
    _blank()

    if sim.get("error_types"):
        _h3("Distribution des erreurs simulées")
        _row("Type d'erreur", "Occurrences")
        _sep("—", "—")
        for et, cnt in sorted(sim["error_types"].items(), key=lambda x: -x[1]):
            _row(et, cnt)
        _blank()

    # Bloc COPY_FOR_ANALYSIS si disponible
    start = sim_stdout.find("=== COPY_FOR_ANALYSIS_START ===")
    end   = sim_stdout.find("=== COPY_FOR_ANALYSIS_END ===")
    if start != -1 and end != -1:
        _h3("Rapport simulation détaillé (COPY_FOR_ANALYSIS)")
        lines.append("```")
        lines.append(sim_stdout[start:end + len("=== COPY_FOR_ANALYSIS_END ===")].strip())
        lines.append("```")
        _blank()

    # ── Calibrations ──────────────────────────────────────────────────────────
    _h2("3. Résultats calibration moteur")
    lines.append(
        "Tous les scripts de calibration opèrent en read-only sur des DB temporaires. "
        "`engine/thresholds.py` n'est jamais modifié."
    )
    _blank()
    _row("Paramètre", "Valeur actuelle", "Script", "Résultat")
    _sep("—", "—", "—", "—")
    _CALIB_PARAMS = [
        ("MASTERY_MIN_ATTEMPTS", "5",       "calibrate_mastery_threshold.py"),
        ("MASTERY_FRAGILE",      "0.60",    "calibrate_mastery_boundaries.py"),
        ("MASTERY_MASTERED",     "0.80",    "calibrate_mastery_boundaries.py"),
        ("ADAPTIVE_FORCE_EASY",  "0.40",    "calibrate_adaptive_difficulty.py"),
        ("ADAPTIVE_ALLOW_HARD",  "0.65",    "calibrate_adaptive_difficulty.py"),
        ("REVIEW_INTERVALS",     "1/3/7 j", "calibrate_review_intervals.py"),
    ]
    _calib_by_script = {c["name"]: c for c in calips}
    for param, val, script in _CALIB_PARAMS:
        short = script.replace("calibrate_", "").replace(".py", "")
        res = _calib_by_script.get(short, {})
        ok = res.get("ok", False)
        _row(f"`{param}`", val, f"`{short}`", "✅ PASS" if ok else "❌ FAIL")
    _blank()

    for c in calips:
        _h3(f"Détail : {c['name']}")
        status = "✅ OK" if c["ok"] else f"❌ FAILED (rc={c['rc']})"
        lines.append(f"**Statut :** {status}")
        _blank()
        if c["missing"]:
            lines.append(f"**Marqueurs absents :** `{'`, `'.join(c['missing'])}`")
            _blank()
        lines.append("**Sortie (fin) :**")
        lines.append("```")
        lines.append(c["stdout_tail"] or "(aucune sortie)")
        lines.append("```")
        _blank()

    # ── Régression ────────────────────────────────────────────────────────────
    _h2("4. Résultats tests de régression")
    if reg is None:
        lines.append("Tests de régression non exécutés (--no-regression ou --quick).")
    else:
        status = "✅ OK" if reg["ok"] else "❌ FAILED"
        lines.append(f"**Statut :** {status}")
        _blank()
        _row("Champ", "Valeur")
        _sep("—", "—")
        _row("Tests exécutés", str(reg["n_tests"]))
        _row("Résultat", "OK" if reg["ok"] else f"FAILED — {reg['detail']}")
        _row("Durée", f"{reg['elapsed']:.1f}s")
        _blank()
    _blank()

    # ── Signaux à surveiller ──────────────────────────────────────────────────
    _h2("5. Signaux à surveiller")
    _signals = [
        ("Score qui chute fortement (< -0.15)",
         (sim.get("d_score") or 0) < -0.15),
        ("Fallback > 20%",
         (sim.get("fb_pct") or 0) > 20),
        ("Alignment curriculum < 20%",
         (sim.get("align_pct") or 100) < 20),
        ("Aucun attempt sauvegardé",
         (sim.get("n_saved") or 0) == 0),
        ("Tests régression KO",
         reg is not None and not reg.get("ok", True)),
    ]
    all_clear = True
    for label, triggered in _signals:
        icon = "⚠️" if triggered else "✅"
        lines.append(f"- {icon} {label}")
        if triggered:
            all_clear = False
    if all_clear:
        _blank()
        lines.append("> Aucun signal anormal détecté.")
    _blank()

    # ── Recommandation finale ─────────────────────────────────────────────────
    _h2("6. Recommandation finale")
    if verdict == "GO SAFE":
        lines.append(textwrap.dedent("""
        Le pipeline moteur est stable et cohérent.

        **Actions recommandées :**
        - Continuer les tests humains avec des données réelles
        - Monitorer le fallback rate sur les premières sessions réelles
        - Recalibrer dans 30j avec des données de rétention réelles
        """).strip())
    elif verdict == "WARNING":
        lines.append(textwrap.dedent("""
        Des signaux anormaux ont été détectés mais aucune défaillance bloquante.

        **Actions recommandées :**
        - Analyser les avertissements listés en section 1
        - Reproduire manuellement sur les sections concernées
        - Ne pas bloquer le merge, mais surveiller en production
        """).strip())
    else:
        lines.append(textwrap.dedent("""
        Des erreurs bloquantes ont été détectées.

        **Actions requises :**
        - Corriger les problèmes listés en section 1 avant de continuer
        - Relancer la suite après correction
        - Ne pas merger tant que le verdict est FAILED
        """).strip())
    _blank()
    lines.append("---")
    lines.append(
        f"*Rapport généré par `run_training_calibration_suite.py` — ADDISCO OPS · {_date_str}*"
    )

    return "\n".join(lines)


# ── Affichage terminal ────────────────────────────────────────────────────────

def _print_phase(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def _print_result(label: str, ok: bool, detail: str = "") -> None:
    icon = "✓" if ok else "✗"
    tail = f" — {detail}" if detail else ""
    print(f"  {icon}  {label}{tail}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    cfg  = _resolve_config(args)

    t_start = time.monotonic()

    print(f"\n{SEP2}")
    print("  ADDISCO OPS — Training & Calibration Suite (TASK-079)")
    print(SEP2)
    print(f"  Utilisateur   : {cfg['user']}")
    print(f"  Mode          : {cfg['mode'].upper()}")
    print(f"  N attempts    : {cfg['n']}")
    print(f"  Régression    : {'oui' if cfg['run_regression'] else 'non'}")
    if cfg["quick"]:
        print("  Preset        : --quick")
    elif cfg["full"]:
        print("  Preset        : --full")
    print(f"  Rapport       : {cfg['output_path']}")

    # Garde API
    if cfg["mode"] == "api" and not cfg["skip_confirm"]:
        print(
            f"\n  ATTENTION : mode API — vrais appels OpenAI ({cfg['n'] * 2} appels estimés)."
        )
        try:
            rep = input("  Confirmer ? [oui/N] : ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            rep = "n"
        if rep not in ("oui", "o", "yes", "y"):
            print("  Annulé.")
            sys.exit(0)

    # ── Phase 1 : Simulation ──────────────────────────────────────────────────
    _print_phase("PHASE 1 — Simulation adaptative")
    print(f"  Lancement : --user {cfg['user']} --n {cfg['n']} --mode {cfg['mode']}")

    _sim_cmd = [
        sys.executable,
        str(ROOT / "tools" / "testing" / "simulate_adaptive_training.py"),
        "--user",   cfg["user"],
        "--n",      str(cfg["n"]),
        "--mode",   cfg["mode"],
        "--seed",   "42",
    ]
    if cfg["mode"] == "api" and cfg["skip_confirm"]:
        _sim_cmd.append("--no-confirm")

    _t0 = time.monotonic()
    sim_rc, sim_stdout, sim_stderr = _run(_sim_cmd, timeout=300)
    sim_elapsed = time.monotonic() - _t0

    sim_data = _parse_simulation(sim_stdout, cfg["n"])

    sim_ok   = sim_rc == 0 and (sim_data.get("n_saved") or 0) > 0
    _sim_detail = f"{sim_data.get('n_saved', '?')}/{cfg['n']} attempts | fallback {sim_data.get('fb_pct', '?')}% | {sim_elapsed:.0f}s"
    _print_result("Simulation", sim_ok, _sim_detail)
    if sim_rc != 0:
        print(f"  [rc={sim_rc}] stderr: {sim_stderr[:200]}")
    if sim_data.get("verdict") and sim_data["verdict"] != "UNKNOWN":
        print(f"  Verdict simulation : {sim_data['verdict']}")

    # ── Phase 2 : Calibrations ────────────────────────────────────────────────
    _print_phase("PHASE 2 — Calibrations moteur")

    _CALIB_SPECS: list[tuple[str, str, list[str]]] = [
        (
            "mastery_threshold",
            str(ROOT / "tools" / "testing" / "calibrate_mastery_threshold.py"),
            ["← actuel", "OK"],
        ),
        (
            "mastery_boundaries",
            str(ROOT / "tools" / "testing" / "calibrate_mastery_boundaries.py"),
            ["4/4 PASS"],
        ),
        (
            "adaptive_difficulty",
            str(ROOT / "tools" / "testing" / "calibrate_adaptive_difficulty.py"),
            ["Invariants : TOUS OK"],
        ),
        (
            "review_intervals",
            str(ROOT / "tools" / "testing" / "calibrate_review_intervals.py"),
            ["4/4 PASS", "Cohérence structurelle : OK"],
        ),
    ]

    calib_results: list[dict] = []
    for name, script, key_strings in _CALIB_SPECS:
        _t0 = time.monotonic()
        rc, stdout, stderr = _run([sys.executable, script], timeout=120)
        elapsed_c = time.monotonic() - _t0
        result = _parse_calib(stdout, rc, key_strings, name)
        calib_results.append(result)
        _print_result(
            f"Calibration {name}",
            result["ok"],
            f"rc={rc} | {elapsed_c:.1f}s"
            + (f" | manquant: {result['missing']}" if result["missing"] else ""),
        )

    # ── Phase 3 : Régression ──────────────────────────────────────────────────
    reg_data: dict | None = None
    if cfg["run_regression"]:
        _print_phase("PHASE 3 — Tests de régression")
        _t0 = time.monotonic()
        reg_rc, reg_stdout, reg_stderr = _run(
            [sys.executable, "test_regression.py"], timeout=180
        )
        reg_elapsed = time.monotonic() - _t0
        reg_data = _parse_regression(reg_stdout, reg_stderr)
        reg_data["elapsed"] = reg_data.get("elapsed") or reg_elapsed
        _print_result(
            "Régression",
            reg_data["ok"],
            f"{reg_data['n_tests']} tests | {reg_data['elapsed']:.1f}s"
            + (f" | {reg_data['detail']}" if reg_data.get("detail") else ""),
        )
    else:
        _print_phase("PHASE 3 — Tests de régression")
        print("  (ignorés — --no-regression ou --quick)")

    # ── Verdict global ────────────────────────────────────────────────────────
    elapsed_total = time.monotonic() - t_start
    verdict, fails, warnings = _compute_verdict(
        sim_data, calib_results, reg_data, cfg["n"]
    )

    print(f"\n{SEP2}")
    _v_icons = {"GO SAFE": "✅", "WARNING": "⚠️", "FAILED": "❌"}
    print(f"  VERDICT GLOBAL : {_v_icons.get(verdict, '?')} {verdict}")
    print(f"  Durée totale   : {elapsed_total:.1f}s")
    if fails:
        for f in fails:
            print(f"     FAILED  · {f}")
    if warnings:
        for w in warnings:
            print(f"     WARNING · {w}")
    if verdict == "GO SAFE":
        print("     Pipeline stable. Prêt pour tests humains.")
    print(SEP2)

    # ── Rapport markdown ──────────────────────────────────────────────────────
    if cfg["full"] or args.output:
        report_md = _build_report(
            cfg           = cfg,
            sim           = sim_data,
            sim_stdout    = sim_stdout,
            calips        = calib_results,
            reg           = reg_data,
            verdict       = verdict,
            fails         = fails,
            warnings      = warnings,
            elapsed_total = elapsed_total,
        )

        out_path = Path(cfg["output_path"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_md, encoding="utf-8")
        print(f"\n  Rapport écrit : {out_path}")

    # Code de sortie : 0 = GO SAFE ou WARNING, 1 = FAILED
    sys.exit(1 if verdict == "FAILED" else 0)


if __name__ == "__main__":
    main()
