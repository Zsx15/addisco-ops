#!/usr/bin/env python
"""
calibrate_adaptive_difficulty.py — TASK-076
Calibration des seuils ADAPTIVE_FORCE_EASY et ADAPTIVE_ALLOW_HARD.

  SECTION A : ADAPTIVE_FORCE_EASY — à quel score récent force-t-on "easy" ?
  SECTION B : ADAPTIVE_ALLOW_HARD — à quel score récent autorise-t-on "hard" ?

Fonction pure get_difficulty_target() : aucun accès DB requis.
Patch en mémoire, restauration garantie.

Usage :
  python tools/testing/calibrate_adaptive_difficulty.py
  python tools/testing/calibrate_adaptive_difficulty.py --force-easy 0.35 0.40 0.45 0.50
  python tools/testing/calibrate_adaptive_difficulty.py --allow-hard 0.60 0.65 0.70 0.75
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(level=logging.WARNING)

import engine.thresholds        as _thr
import engine.adaptive_difficulty as _adiff

SEP  = "─" * 72
SEP2 = "━" * 72

_ORIG_FORCE_EASY = _thr.ADAPTIVE_FORCE_EASY
_ORIG_ALLOW_HARD = _thr.ADAPTIVE_ALLOW_HARD

# Candidats par défaut
_DEFAULT_FORCE_EASY = [0.35, 0.40, 0.45, 0.50]
_DEFAULT_ALLOW_HARD = [0.60, 0.65, 0.70, 0.75]

# Scores récents testés
# SECTION A : straddlent FORCE_EASY (zone 0.30–0.55)
_FORCE_EASY_TEST_AVGS = [0.28, 0.33, 0.37, 0.40, 0.43, 0.47, 0.52, 0.57]
# SECTION B : straddlent ALLOW_HARD, au-dessus de FORCE_EASY (zone 0.55–0.82)
_ALLOW_HARD_TEST_AVGS = [0.55, 0.60, 0.63, 0.65, 0.68, 0.70, 0.75, 0.82]


# ── Patch / restore ───────────────────────────────────────────────────────────

def _patch_force_easy(v: float) -> None:
    _thr.ADAPTIVE_FORCE_EASY      = v
    _adiff.SCORE_FORCE_EASY       = v


def _patch_allow_hard(v: float) -> None:
    _thr.ADAPTIVE_ALLOW_HARD      = v
    _adiff.SCORE_ALLOW_HARD       = v


def _restore() -> None:
    _thr.ADAPTIVE_FORCE_EASY      = _ORIG_FORCE_EASY
    _thr.ADAPTIVE_ALLOW_HARD      = _ORIG_ALLOW_HARD
    _adiff.SCORE_FORCE_EASY       = _ORIG_FORCE_EASY
    _adiff.SCORE_ALLOW_HARD       = _ORIG_ALLOW_HARD


# ── Analyse pure ──────────────────────────────────────────────────────────────

def _difficulty(recent_avg: float, mastery: str, graph_level: int) -> str:
    return _adiff.get_difficulty_target(mastery, [recent_avg] * 5, graph_level)


def analyze_force_easy(
    candidates: list[float],
    test_avgs: list[float],
    mastery: str = "Maîtrisé",
    graph_level: int = 2,
) -> dict:
    """
    Pour chaque valeur de FORCE_EASY, applique get_difficulty_target
    sur chaque score récent avec mastery='Maîtrisé' (cas où FORCE_EASY est actif).
    Sans FORCE_EASY, le résultat serait 'hard' (Maîtrisé + avg >= ALLOW_HARD)
    ou 'medium' (avg < ALLOW_HARD). FORCE_EASY le passe en 'easy'.
    """
    try:
        matrix: dict[float, dict[float, str]] = {}
        for fev in candidates:
            _patch_force_easy(fev)
            matrix[fev] = {
                avg: _difficulty(avg, mastery, graph_level)
                for avg in test_avgs
            }
        return matrix
    finally:
        _restore()


def analyze_allow_hard(
    candidates: list[float],
    test_avgs: list[float],
    mastery: str = "Maîtrisé",
    graph_level: int = 2,
) -> dict:
    """
    Pour chaque valeur de ALLOW_HARD, applique get_difficulty_target
    sur chaque score récent avec mastery='Maîtrisé'.
    Tous les avgs testés sont > FORCE_EASY (0.40) donc pas de forced easy.
    Mesure uniquement la transition medium → hard.
    """
    try:
        matrix: dict[float, dict[float, str]] = {}
        for ahv in candidates:
            _patch_allow_hard(ahv)
            matrix[ahv] = {
                avg: _difficulty(avg, mastery, graph_level)
                for avg in test_avgs
            }
        return matrix
    finally:
        _restore()


# ── Affichage ─────────────────────────────────────────────────────────────────

_SHORT = {"easy": "E", "medium": "M", "hard": "H"}


def _print_table(
    matrix: dict,
    test_avgs: list[float],
    param_name: str,
    current_val: float,
) -> None:
    print(f"  {param_name:<22}", end="")
    for avg in test_avgs:
        print(f"  {avg:.2f} ", end="")
    print()
    print("  " + "─" * (22 + len(test_avgs) * 8))

    for pv, row in sorted(matrix.items()):
        tag = " ←" if abs(pv - current_val) < 0.001 else "  "
        line = f"  {pv:.2f}{tag:<18}"
        prev: Optional[str] = None
        for avg in sorted(test_avgs):
            diff = row[avg]
            sep = "│" if (prev is not None and prev != diff) else " "
            line += f"  {sep}{_SHORT.get(diff, diff[0])}      "
            prev = diff
        print(line)

    print()
    print("  E=easy  M=medium  H=hard  │=transition  ←=valeur actuelle")


# ── Recommandations ───────────────────────────────────────────────────────────

def _find_transition(row: dict[float, str], from_label: str, to_label: str) -> Optional[float]:
    sorted_avgs = sorted(row.keys())
    prev: Optional[str] = None
    for avg in sorted_avgs:
        if row[avg] == to_label and prev == from_label:
            return avg
        prev = row[avg]
    return None


def recommend_force_easy(matrix: dict, current: float) -> str:
    lines: list[str] = []
    for fev, row in sorted(matrix.items()):
        t = _find_transition(row, "easy", "medium")
        if t is None:
            all_vals = set(row.values())
            verdict = "TROP_STRICT (tout easy)" if all_vals == {"easy"} \
                      else "TROP_PERMISSIF (jamais easy)"
        elif t < 0.36:
            verdict = "TROP_PERMISSIF (n'intervient qu'aux très bas scores)"
        elif t <= 0.47:
            verdict = "OK"
        else:
            verdict = "TROP_STRICT (force easy même pour les scores moyens)"
        mark = " ← actuel" if abs(fev - current) < 0.001 else ""
        lines.append(f"  FORCE_EASY={fev:.2f} : transition E→M à avg {t or '—'} → {verdict}{mark}")
    return "\n".join(lines)


def recommend_allow_hard(matrix: dict, current: float) -> str:
    lines: list[str] = []
    for ahv, row in sorted(matrix.items()):
        t = _find_transition(row, "medium", "hard")
        if t is None:
            all_vals = set(row.values())
            verdict = "TROP_STRICT (jamais hard)" if "hard" not in all_vals \
                      else "TROP_PERMISSIF (tout hard)"
        elif t < 0.61:
            verdict = "TROP_PERMISSIF (hard autorisé trop tôt)"
        elif t <= 0.72:
            verdict = "OK"
        else:
            verdict = "TROP_STRICT (hard presque inaccessible)"
        mark = " ← actuel" if abs(ahv - current) < 0.001 else ""
        lines.append(f"  ALLOW_HARD={ahv:.2f} : transition M→H à avg {t or '—'} → {verdict}{mark}")
    return "\n".join(lines)


# ── Copy block ────────────────────────────────────────────────────────────────

def _copy_block(
    force_matrix: dict,
    hard_matrix: dict,
    force_avgs: list[float],
    hard_avgs: list[float],
) -> str:
    lines = ["=== COPY_FOR_ANALYSIS_START ==="]
    lines.append("# Adaptive Difficulty Calibration — TASK-076")
    lines.append(f"- ADAPTIVE_FORCE_EASY actuel : {_ORIG_FORCE_EASY}")
    lines.append(f"- ADAPTIVE_ALLOW_HARD actuel : {_ORIG_ALLOW_HARD}")
    lines.append(f"- Contexte test : mastery=Maîtrisé, graph_level=2")
    lines.append("")

    lines.append("## SECTION A — ADAPTIVE_FORCE_EASY")
    lines.append("| FORCE_EASY | " + " | ".join(f"avg={a:.2f}" for a in sorted(force_avgs)) + " |")
    lines.append("|" + "---|" * (1 + len(force_avgs)))
    for fev, row in sorted(force_matrix.items()):
        mark = " ←" if abs(fev - _ORIG_FORCE_EASY) < 0.001 else ""
        cells = " | ".join(_SHORT.get(row[a], "?") for a in sorted(force_avgs))
        lines.append(f"| {fev:.2f}{mark} | {cells} |")
    lines.append("")

    lines.append("## SECTION B — ADAPTIVE_ALLOW_HARD")
    lines.append("| ALLOW_HARD | " + " | ".join(f"avg={a:.2f}" for a in sorted(hard_avgs)) + " |")
    lines.append("|" + "---|" * (1 + len(hard_avgs)))
    for ahv, row in sorted(hard_matrix.items()):
        mark = " ←" if abs(ahv - _ORIG_ALLOW_HARD) < 0.001 else ""
        cells = " | ".join(_SHORT.get(row[a], "?") for a in sorted(hard_avgs))
        lines.append(f"| {ahv:.2f}{mark} | {cells} |")
    lines.append("")
    lines.append("=== COPY_FOR_ANALYSIS_END ===")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive Difficulty Calibration — TASK-076")
    parser.add_argument("--force-easy", nargs="+", type=float, default=_DEFAULT_FORCE_EASY)
    parser.add_argument("--allow-hard", nargs="+", type=float, default=_DEFAULT_ALLOW_HARD)
    args = parser.parse_args()

    print(f"\n{SEP2}")
    print("  ADDISCO OPS — Adaptive Difficulty Calibration (TASK-076)")
    print(SEP2)
    print(f"  ADAPTIVE_FORCE_EASY candidats : {args.force_easy}")
    print(f"  ADAPTIVE_ALLOW_HARD candidats : {args.allow_hard}")
    print(f"  Valeurs actuelles             : FORCE_EASY={_ORIG_FORCE_EASY}  ALLOW_HARD={_ORIG_ALLOW_HARD}")
    print(f"  Contexte test                 : mastery=Maîtrisé, graph_level=2, window=5 scores")

    # ── SECTION A ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION A — ADAPTIVE_FORCE_EASY : forçage mode easy")
    print("  Question : à quel score récent moyen le moteur force-t-il easy ?")
    print(f"  Setup    : mastery=Maîtrisé — sans ce seuil, le résultat serait medium/hard")
    print(SEP)

    force_matrix = analyze_force_easy(args.force_easy, _FORCE_EASY_TEST_AVGS)
    _print_table(force_matrix, _FORCE_EASY_TEST_AVGS, "FORCE_EASY", _ORIG_FORCE_EASY)

    print("  Recommandations :")
    print(recommend_force_easy(force_matrix, _ORIG_FORCE_EASY))
    print("\n  Enjeu pédagogique :")
    print("  - Trop bas (0.35) : apprenants en difficulté ne bénéficient pas du mode easy")
    print("  - Trop haut (0.50) : le moteur force easy même pour des apprenants qui progressent")
    print("  - Fenêtre OK : transition E→M entre avg 0.36 et 0.47")

    # ── SECTION B ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION B — ADAPTIVE_ALLOW_HARD : autorisation mode hard")
    print("  Question : à quel score récent moyen le moteur autorise-t-il hard ?")
    print(f"  Setup    : mastery=Maîtrisé, avgs > FORCE_EASY=0.40 (forced easy inactif)")
    print(SEP)

    hard_matrix = analyze_allow_hard(args.allow_hard, _ALLOW_HARD_TEST_AVGS)
    _print_table(hard_matrix, _ALLOW_HARD_TEST_AVGS, "ALLOW_HARD", _ORIG_ALLOW_HARD)

    print("  Recommandations :")
    print(recommend_allow_hard(hard_matrix, _ORIG_ALLOW_HARD))
    print("\n  Enjeu pédagogique :")
    print("  - Trop bas (0.60) : questions difficiles trop tôt, risque de découragement")
    print("  - Trop haut (0.75) : apprenants solides restent en medium, sous-challengés")
    print("  - Fenêtre OK : transition M→H entre avg 0.61 et 0.72")

    # ── Vérifications croisées ────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  VÉRIFICATIONS CROISÉES (valeurs actuelles)")
    print(SEP)
    _verify_cross_checks()

    # ── Synthèse ──────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("  SYNTHÈSE")
    print(SEP2)

    if _ORIG_FORCE_EASY in force_matrix:
        t = _find_transition(force_matrix[_ORIG_FORCE_EASY], "easy", "medium")
        print(f"  FORCE_EASY={_ORIG_FORCE_EASY} : transition E→M à avg {t or '—'}")
    if _ORIG_ALLOW_HARD in hard_matrix:
        t = _find_transition(hard_matrix[_ORIG_ALLOW_HARD], "medium", "hard")
        print(f"  ALLOW_HARD={_ORIG_ALLOW_HARD} : transition M→H à avg {t or '—'}")

    gap = _ORIG_ALLOW_HARD - _ORIG_FORCE_EASY
    print(f"  Écart ALLOW_HARD - FORCE_EASY : {gap:.2f}  "
          f"({'OK — zone medium bien définie' if gap >= 0.20 else 'ATTENTION — zone medium trop étroite'})")

    # ── Copy block ────────────────────────────────────────────────────────────
    block = _copy_block(
        force_matrix, hard_matrix,
        _FORCE_EASY_TEST_AVGS, _ALLOW_HARD_TEST_AVGS,
    )
    print(f"\n{block}\n")


def _verify_cross_checks() -> None:
    """Vérifie les invariants importants avec les valeurs actuelles."""
    cases = [
        # (recent_avg, mastery, graph_level, expected_difficulty, description)
        (0.35, "Maîtrisé",         2, "easy",   "avg < FORCE_EASY → easy même si Maîtrisé"),
        (0.35, "Fragile",          2, "easy",   "avg < FORCE_EASY → easy même si déjà Fragile"),
        (0.50, "Maîtrisé",         2, "medium", "avg entre FORCE et ALLOW → medium (Maîtrisé)"),
        (0.50, "En consolidation", 2, "medium", "En consolidation → medium (normal)"),
        (0.50, "Fragile",          2, "easy",   "Fragile → easy (mastery override)"),
        (0.70, "Maîtrisé",         2, "hard",   "avg >= ALLOW_HARD + Maîtrisé → hard"),
        (0.70, "En consolidation", 2, "medium", "avg >= ALLOW_HARD mais En consolidation → medium"),
        (0.70, "Maîtrisé",         1, "medium", "graph_level=1 (fondation) → jamais hard"),
        (0.35, "Maîtrisé",         1, "easy",   "avg < FORCE_EASY + fondation → easy"),
    ]

    all_pass = True
    for (avg, mastery, glevel, expected, desc) in cases:
        observed = _adiff.get_difficulty_target(mastery, [avg] * 5, glevel)
        icon = "✓" if observed == expected else "✗"
        if observed != expected:
            all_pass = False
        print(f"  {icon}  avg={avg}  mastery={mastery:<15}  glevel={glevel}  "
              f"attendu={expected:<7}  observé={observed}  — {desc}")

    print(f"\n  Invariants : {'TOUS OK' if all_pass else 'ECHEC — comportement inattendu'}")


if __name__ == "__main__":
    main()
