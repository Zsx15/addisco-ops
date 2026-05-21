"""
Smoke test — Profil pédagogique enrichi V1 (TASK-049).

Usage (depuis la racine du projet) :
    python tools/qa/test_profile_insights_smoke.py --username test
    python tools/qa/test_profile_insights_smoke.py --username admin

Lecture seule : aucun write SQL, aucun appel API.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

# ── Chemin racine ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import database as db
from engine.user_profile_insights import compute_profile_insights

# ── Couleurs ANSI ─────────────────────────────────────────────────────────────
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_BLUE   = "\033[94m"
_GREY   = "\033[90m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

_CONFIDENCE_COLOR = {"high": _GREEN, "medium": _YELLOW, "low": _GREY}


def _hr(char: str = "-", n: int = 60) -> None:
    print(_GREY + char * n + _RESET)


def _header(title: str) -> None:
    _hr("=")
    print(f"{_BOLD}{title}{_RESET}")
    _hr("=")


def _section(title: str) -> None:
    print(f"\n{_BLUE}{_BOLD}{title}{_RESET}")
    _hr("-", 40)


def resolve_user(username: str) -> tuple[str | None, str | None]:
    """Retourne (user_id, role) depuis le username, ou (None, None) si absent."""
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT user_id, role FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return None, None
    return row["user_id"], row["role"]


def get_attempts_count(user_id: str) -> int:
    with sqlite3.connect(db.DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row[0]) if row else 0


def get_learning_profile(user_id: str) -> dict | None:
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM user_learning_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    if d.get("fragile_topics"):
        try:
            d["fragile_topics"] = json.loads(d["fragile_topics"])
        except (json.JSONDecodeError, TypeError):
            d["fragile_topics"] = []
    return d


def get_error_counts(user_id: str) -> dict[str, int]:
    with sqlite3.connect(db.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT error_type, COUNT(*) as cnt
            FROM attempts
            WHERE user_id = ?
              AND error_type IS NOT NULL
              AND error_type != 'correct'
              AND error_type != ''
            GROUP BY error_type
            ORDER BY cnt DESC
            """,
            (user_id,),
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def get_avg_response_time(user_id: str) -> float | None:
    with sqlite3.connect(db.DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT AVG(response_time_seconds)
            FROM attempts
            WHERE user_id = ?
              AND response_time_seconds IS NOT NULL
              AND response_time_seconds > 0
            """,
            (user_id,),
        ).fetchone()
    val = row[0] if row else None
    return round(float(val), 1) if val is not None else None


def run_smoke(username: str) -> bool:
    _header("Smoke test -- Profil pedagogique enrichi V1")
    print(f"Utilisateur ciblé : {_BOLD}{username}{_RESET}")

    # ── 1. Résolution user ────────────────────────────────────────────────────
    user_id, role = resolve_user(username)
    if user_id is None:
        print(f"\n{_RED}KO Utilisateur '{username}' introuvable en base.{_RESET}")
        print("  Vérifiez le username avec : SELECT username FROM users;")
        return False
    print(f"user_id : {_GREY}{user_id}{_RESET}")
    print(f"role    : {role}")

    # ── 2. Attempts ───────────────────────────────────────────────────────────
    _section("Données brutes")
    total = get_attempts_count(user_id)
    print(f"Attempts totaux    : {_BOLD}{total}{_RESET}")

    if total == 0:
        print(f"{_YELLOW}! Aucune tentative — les insights seront vides (confidence=low).{_RESET}")

    # ── 3. Profil stocké ──────────────────────────────────────────────────────
    profile = get_learning_profile(user_id)
    if profile is None:
        print(f"{_YELLOW}! Profil non calculé en base.{_RESET}")
        print("  -> Connectez-vous et cliquez sur 'Calculer le profil' dans le Dashboard.")
        print("  -> Le smoke test continue avec des valeurs à zéro (données partielles).")
        profile = {}

    avg_score  = float(profile.get("average_score") or 0.0)
    pref       = profile.get("preferred_pedagogy")
    fragile    = profile.get("fragile_topics") or []
    momentum   = float(profile.get("momentum") or 0.0)
    consistency = float(profile.get("consistency_score") or 0.0)

    print(f"avg_score          : {round(avg_score * 100)} %")
    print(f"preferred_pedagogy : {pref or '—'}")
    print(f"fragile_topics     : {fragile or '(aucun)'}")
    print(f"momentum           : {momentum:+.3f}")
    print(f"consistency_score  : {round(consistency * 100)} %")

    # ── 4. Erreurs + temps ────────────────────────────────────────────────────
    err_counts = get_error_counts(user_id)
    avg_rt     = get_avg_response_time(user_id)
    print(f"error_type_counts  : {err_counts or '(aucun)'}")
    print(f"avg_response_time  : {f'{avg_rt} s' if avg_rt else '—'}")

    # ── 5. Appel compute_profile_insights ────────────────────────────────────
    _section("compute_profile_insights()")
    data = {
        "total_attempts":     total,
        "avg_score":          avg_score,
        "preferred_pedagogy": pref,
        "logical_score":      float(profile.get("logical_score") or 0.0),
        "procedural_score":   float(profile.get("procedural_score") or 0.0),
        "narrative_score":    float(profile.get("narrative_score") or 0.0),
        "analogy_score":      float(profile.get("analogy_score") or 0.0),
        "fragile_topics":     fragile,
        "momentum":           momentum,
        "consistency_score":  consistency,
        "error_type_counts":  err_counts,
        "avg_response_time":  avg_rt,
    }

    try:
        ins = compute_profile_insights(data)
    except Exception as exc:
        print(f"{_RED}KO Exception dans compute_profile_insights : {exc}{_RESET}")
        return False

    # ── 6. Affichage résultats ────────────────────────────────────────────────
    conf_col  = _CONFIDENCE_COLOR.get(ins["confidence"], _GREY)
    _ped_colors = {"strong": _GREEN, "moderate": _YELLOW, "weak": _GREY}
    _ped_col = _ped_colors.get(ins.get("pedagogical_signal") or "", _GREY)
    print(f"Confiance statistique : {conf_col}{_BOLD}{ins['confidence_label']}{_RESET}")
    if ins.get("pedagogical_signal"):
        print(f"Signal pédagogique    : {_ped_col}{_BOLD}{ins['pedagogical_signal_label']}{_RESET}")

    if ins["dominant_style_label"]:
        print(f"Style     : {ins['dominant_style_label']}")
    elif ins["dominant_style"]:
        print(f"Style     : {ins['dominant_style']}")
    else:
        print(f"Style     : {_GREY}(indéterminé){_RESET}")

    _section("Points forts observés")
    if ins["strengths"]:
        for s in ins["strengths"]:
            print(f"  {_GREEN}+{_RESET} {s}")
    else:
        print(f"  {_GREY}(aucun){_RESET}")

    _section("Fragilités observées")
    if ins["weaknesses"]:
        for w in ins["weaknesses"]:
            print(f"  {_YELLOW}!{_RESET} {w}")
    else:
        print(f"  {_GREY}(aucune){_RESET}")

    _section("Recommandations pédagogiques")
    for r in ins["recommendations"]:
        print(f"  {_BLUE}>{_RESET} {r}")

    _section("Signaux utilisés")
    for k, v in ins["signals_used"].items():
        print(f"  {_GREY}{k}{_RESET} : {v}")

    # ── 7. Vérifications minimales ────────────────────────────────────────────
    _section("Vérifications")
    checks_ok = True

    required_keys = (
        "dominant_style", "dominant_style_key", "dominant_style_label",
        "strengths", "weaknesses", "recommendations",
        "confidence", "confidence_label", "signals_used",
        "pedagogical_signal", "pedagogical_signal_label",
    )
    for key in required_keys:
        if key not in ins:
            print(f"  {_RED}KO Clé manquante : '{key}'{_RESET}")
            checks_ok = False

    if ins["confidence"] not in ("low", "medium", "high"):
        print(f"  {_RED}KO confidence invalide : '{ins['confidence']}'{_RESET}")
        checks_ok = False

    if not isinstance(ins["recommendations"], list) or len(ins["recommendations"]) == 0:
        print(f"  {_RED}KO recommendations vide ou invalide{_RESET}")
        checks_ok = False

    if "correct" in ins.get("signals_used", {}):
        print(f"  {_YELLOW}! 'correct' présent dans signals_used — à vérifier{_RESET}")

    if checks_ok:
        print(f"  {_GREEN}OK Toutes les clés présentes{_RESET}")
        print(f"  {_GREEN}OK confidence valide : {ins['confidence']}{_RESET}")
        print(f"  {_GREEN}OK recommendations non vides{_RESET}")

    _hr("=")
    if checks_ok:
        print(f"{_GREEN}{_BOLD}VERDICT : GO SAFE{_RESET}")
    else:
        print(f"{_RED}{_BOLD}VERDICT : FAILED{_RESET}")
    _hr("=")

    return checks_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke test — Profil pédagogique enrichi V1 (TASK-049)"
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Nom d'utilisateur à tester (ex: test, admin)",
    )
    args = parser.parse_args()
    ok = run_smoke(args.username)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
