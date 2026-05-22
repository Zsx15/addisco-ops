"""
Runtime Analytics — TASK-070
Script standalone read-only : analyse des métriques runtime LLM.

Usage :
    python tools/observability/runtime_analytics.py [--hours N]

Affiche :
  1. Latence (moyenne + P95 par endpoint)
  2. Coût estimé (global + par user + par document)
  3. Qualité runtime (succès / fallback / erreurs / appels lents)
  4. Santé pédagogique (scores par question_type, taux non_evaluable)
  5. Utilisateurs (top consommateurs API, sessions anormales)

Verdict final : OK / WARNING / CRITICAL
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# ── Encodage terminal Windows ─────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Chemin DB ─────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

import database as _db  # noqa: E402 — après sys.path

# ── Constantes ────────────────────────────────────────────────────────────────
SLOW_CALL_THRESHOLD_MS = 3_000
FALLBACK_WARNING_PCT   = 10.0
FALLBACK_CRITICAL_PCT  = 25.0
SUCCESS_WARNING_PCT    = 90.0
SUCCESS_CRITICAL_PCT   = 75.0
LATENCY_WARNING_MS     = 2_000
LATENCY_CRITICAL_MS    = 4_000

SEP  = "─" * 64
SEP2 = "━" * 64


# ── Helpers ───────────────────────────────────────────────────────────────────

def _q(sql: str, params: tuple = ()) -> list[dict]:
    try:
        with sqlite3.connect(_db.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        print(f"  [QUERY ERROR] {exc}")
        return []


def _scalar(sql: str, params: tuple = (), default=0):
    rows = _q(sql, params)
    if not rows:
        return default
    val = list(rows[0].values())[0]
    return val if val is not None else default


def _badge(value: float, warn: float, crit: float, higher_is_bad: bool = True) -> str:
    if higher_is_bad:
        if value >= crit:
            return "CRITICAL"
        if value >= warn:
            return "WARNING"
        return "OK"
    else:
        if value <= crit:
            return "CRITICAL"
        if value <= warn:
            return "WARNING"
        return "OK"


def _print_badge(label: str, value: str, unit: str = "", badge: str = "OK") -> None:
    icons = {"OK": "✓", "WARNING": "⚠", "CRITICAL": "✗"}
    icon = icons.get(badge, "·")
    print(f"  {icon} {label:<35} {value}{unit}  [{badge}]")


# ── Sections ──────────────────────────────────────────────────────────────────

def section_latency(interval: str) -> list[str]:
    print(f"\n{SEP}")
    print("  1. LATENCE")
    print(SEP)
    issues: list[str] = []

    rows = _q(
        """
        SELECT endpoint,
               COUNT(*)                          AS calls,
               ROUND(AVG(latency_ms))            AS avg_ms,
               MAX(latency_ms)                   AS max_ms,
               SUM(CASE WHEN latency_ms > ? THEN 1 ELSE 0 END) AS slow
        FROM runtime_metrics
        WHERE timestamp >= datetime('now', ?) AND latency_ms IS NOT NULL
        GROUP BY endpoint
        ORDER BY avg_ms DESC
        """,
        (SLOW_CALL_THRESHOLD_MS, interval),
    )

    if not rows:
        print("  Aucune métrique de latence disponible.")
        return issues

    for r in rows:
        badge = _badge(r["avg_ms"], LATENCY_WARNING_MS, LATENCY_CRITICAL_MS)
        _print_badge(
            f"{r['endpoint']} ({r['calls']} appels)",
            f"moy={r['avg_ms']}ms  max={r['max_ms']}ms  lents={r['slow']}",
            badge=badge,
        )
        if badge != "OK":
            issues.append(f"Latence {badge} sur {r['endpoint']} : moy={r['avg_ms']}ms")

    return issues


def section_cost(interval: str) -> list[str]:
    print(f"\n{SEP}")
    print("  2. COÛT ESTIMÉ")
    print(SEP)
    issues: list[str] = []

    total_cost = _scalar(
        "SELECT ROUND(SUM(COALESCE(estimated_cost,0)),6) FROM runtime_metrics WHERE timestamp >= datetime('now',?)",
        (interval,),
        0.0,
    )
    total_tokens = _scalar(
        "SELECT SUM(COALESCE(tokens_input,0)+COALESCE(tokens_output,0)) FROM runtime_metrics WHERE timestamp >= datetime('now',?)",
        (interval,),
        0,
    )
    print(f"  · Coût total estimé    : ${total_cost:.6f}")
    print(f"  · Tokens totaux        : {total_tokens:,}")

    print("\n  Top utilisateurs (coût) :")
    user_rows = _q(
        """
        SELECT user_id,
               COUNT(*) AS calls,
               ROUND(SUM(COALESCE(estimated_cost,0)),6) AS cost,
               SUM(COALESCE(tokens_input,0)+COALESCE(tokens_output,0)) AS tokens
        FROM runtime_metrics
        WHERE timestamp >= datetime('now',?)
        GROUP BY user_id ORDER BY cost DESC LIMIT 10
        """,
        (interval,),
    )
    for r in user_rows:
        print(f"    {r['user_id']:<20} {r['calls']} appels  ${r['cost']:.6f}  {r['tokens']:,} tokens")

    return issues


def section_quality(interval: str) -> list[str]:
    print(f"\n{SEP}")
    print("  3. QUALITÉ RUNTIME")
    print(SEP)
    issues: list[str] = []

    total = _scalar("SELECT COUNT(*) FROM runtime_metrics WHERE timestamp >= datetime('now',?)", (interval,), 0)
    if total == 0:
        print("  Aucune métrique disponible.")
        return issues

    success_rate = _scalar(
        "SELECT ROUND(AVG(success)*100,1) FROM runtime_metrics WHERE timestamp >= datetime('now',?)",
        (interval,),
        100.0,
    )
    fallback_rate = _scalar(
        "SELECT ROUND(AVG(fallback_used)*100,1) FROM runtime_metrics WHERE timestamp >= datetime('now',?)",
        (interval,),
        0.0,
    )
    slow_count = _scalar(
        f"SELECT COUNT(*) FROM runtime_metrics WHERE timestamp >= datetime('now',?) AND latency_ms > {SLOW_CALL_THRESHOLD_MS}",
        (interval,),
        0,
    )

    badge_ok = _badge(success_rate, SUCCESS_WARNING_PCT, SUCCESS_CRITICAL_PCT, higher_is_bad=False)
    badge_fb = _badge(fallback_rate, FALLBACK_WARNING_PCT, FALLBACK_CRITICAL_PCT)

    _print_badge("Taux de succès", f"{success_rate}%", badge=badge_ok)
    _print_badge("Taux fallback", f"{fallback_rate}%", badge=badge_fb)
    _print_badge("Appels lents (>3s)", str(slow_count), badge="WARNING" if slow_count > 0 else "OK")
    _print_badge("Total appels", str(total), badge="OK")

    if badge_ok != "OK":
        issues.append(f"Taux de succès {badge_ok} : {success_rate}%")
    if badge_fb != "OK":
        issues.append(f"Taux fallback {badge_fb} : {fallback_rate}%")
    if slow_count > 5:
        issues.append(f"{slow_count} appels lents détectés")

    err_rows = _q(
        """
        SELECT error_type, COUNT(*) AS n
        FROM runtime_metrics
        WHERE timestamp >= datetime('now',?) AND error_type IS NOT NULL
        GROUP BY error_type ORDER BY n DESC LIMIT 8
        """,
        (interval,),
    )
    if err_rows:
        print("\n  Top erreurs :")
        for r in err_rows:
            print(f"    {r['n']:>4}x  {r['error_type']}")

    return issues


def section_pedagogy(interval: str) -> list[str]:
    print(f"\n{SEP}")
    print("  4. SANTÉ PÉDAGOGIQUE")
    print(SEP)
    issues: list[str] = []

    try:
        rows = _q(
            """
            SELECT pedagogy_type,
                   COUNT(*) AS n,
                   ROUND(AVG(score)*100,1) AS avg_score_pct
            FROM attempts
            WHERE created_at >= datetime('now', ?)
            GROUP BY pedagogy_type ORDER BY n DESC
            """,
            (interval,),
        )
        if not rows:
            print("  Aucune tentative dans la période.")
        else:
            print("  Score moyen par type de question :")
            for r in rows:
                qtype = r["pedagogy_type"] or "inconnu"
                badge = "OK" if (r["avg_score_pct"] or 0) >= 50 else "WARNING"
                _print_badge(f"{qtype} ({r['n']} tentatives)", f"{r['avg_score_pct'] or 0:.1f}%", badge=badge)
                if badge != "OK":
                    issues.append(f"Score faible sur {qtype} : {r['avg_score_pct']}%")

        # Taux non_evaluable
        ne_count = _scalar(
            "SELECT COUNT(*) FROM attempts WHERE created_at >= datetime('now',?) AND score IS NULL",
            (interval,),
            0,
        )
        total_att = _scalar(
            "SELECT COUNT(*) FROM attempts WHERE created_at >= datetime('now',?)",
            (interval,),
            0,
        )
        if total_att > 0:
            ne_pct = round(ne_count / total_att * 100, 1)
            badge = _badge(ne_pct, 10.0, 25.0)
            _print_badge("Taux non_evaluable", f"{ne_pct}%", badge=badge)
            if badge != "OK":
                issues.append(f"Taux non_evaluable {badge} : {ne_pct}%")

        # Top documents problématiques (score moyen faible)
        doc_rows = _q(
            """
            SELECT a.document_id, COUNT(*) AS n, ROUND(AVG(a.score)*100,1) AS avg_score
            FROM attempts a
            WHERE a.created_at >= datetime('now',?) AND a.document_id IS NOT NULL AND a.score IS NOT NULL
            GROUP BY a.document_id HAVING n >= 3
            ORDER BY avg_score ASC LIMIT 5
            """,
            (interval,),
        )
        if doc_rows:
            print("\n  Documents problématiques (score < 50%) :")
            for r in doc_rows:
                if (r["avg_score"] or 100) < 50:
                    print(f"    doc_id={r['document_id']}  {r['n']} tentatives  score={r['avg_score']}%")

    except Exception as exc:
        print(f"  [ERREUR] {exc}")

    return issues


def section_users(interval: str) -> list[str]:
    print(f"\n{SEP}")
    print("  5. UTILISATEURS")
    print(SEP)
    issues: list[str] = []

    print("  Top consommateurs API :")
    user_rows = _q(
        """
        SELECT user_id, COUNT(*) AS calls,
               ROUND(AVG(latency_ms)) AS avg_ms
        FROM runtime_metrics
        WHERE timestamp >= datetime('now',?)
        GROUP BY user_id ORDER BY calls DESC LIMIT 10
        """,
        (interval,),
    )
    for r in user_rows:
        print(f"    {r['user_id']:<20} {r['calls']:>5} appels  avg={r['avg_ms'] or 0:.0f}ms")

    print("\n  Sessions anormales (> 50 appels en 1h) :")
    heavy_rows = _q(
        """
        SELECT user_id, COUNT(*) AS calls
        FROM runtime_metrics
        WHERE timestamp >= datetime('now', '-1 hours')
        GROUP BY user_id HAVING calls > 50
        ORDER BY calls DESC
        """,
        (),
    )
    if heavy_rows:
        for r in heavy_rows:
            print(f"    ⚠  {r['user_id']}  {r['calls']} appels / heure")
            issues.append(f"Session anormale : {r['user_id']} ({r['calls']} appels/h)")
    else:
        print("    Aucune session anormale détectée.")

    return issues


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Runtime Analytics — ADDISCO OPS")
    parser.add_argument("--hours", type=int, default=24, help="Fenêtre d'analyse en heures (défaut: 24)")
    args = parser.parse_args()

    hours    = args.hours
    interval = f"-{hours} hours"

    print(f"\n{SEP2}")
    print(f"  ADDISCO OPS — Runtime Analytics")
    print(f"  Fenêtre : {hours}h  |  DB : {_db.DB_PATH}")
    print(SEP2)

    # Vérifier que la table existe
    try:
        _scalar("SELECT COUNT(*) FROM runtime_metrics", default=0)
    except Exception:
        print("\n  [ERREUR] Table runtime_metrics introuvable — lancez d'abord l'application.")
        sys.exit(1)

    all_issues: list[str] = []
    all_issues += section_latency(interval)
    all_issues += section_cost(interval)
    all_issues += section_quality(interval)
    all_issues += section_pedagogy(interval)
    all_issues += section_users(interval)

    # ── Verdict ──────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    has_critical = any("CRITICAL" in i for i in all_issues)
    has_warning  = bool(all_issues)

    if has_critical:
        verdict = "CRITICAL"
    elif has_warning:
        verdict = "WARNING"
    else:
        verdict = "OK"

    print(f"  VERDICT : {verdict}")
    if all_issues:
        print()
        for issue in all_issues:
            print(f"  · {issue}")
    print(SEP2)
    print()

    sys.exit(1 if verdict == "CRITICAL" else 0)


if __name__ == "__main__":
    main()
