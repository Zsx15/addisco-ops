"""
curriculum_observer.py -- Observer CLI TASK-058

Affiche la recommandation curriculum pour un utilisateur :
  - Prochaine etape pedagogique
  - Queue complete (max 10)
  - Skills fragiles + patterns actifs
  - Difficultes choisies + raisons detaillees
  - Fallbacks eventuels

Usage :
  python tools/observability/curriculum_observer.py [user_id]
  python tools/observability/curriculum_observer.py Guilhem
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.curriculum_engine import get_curriculum_recommendation
import database as _db


_SOURCE_ICON = {
    "error_pattern": "[ERR]",
    "skill_mastery":  "[SKL]",
    "revision":       "[REV]",
    "fallback":       "[---]",
}

_DIFF_ICON = {
    "easy":   "(E)",
    "medium": "(M)",
    "hard":   "(H)",
}

_TREND_LABEL = {
    "critique":         "CRITIQUE",
    "chronique":        "CHRONIQUE",
    "recent":           "RECENT",
    "en_amelioration":  "amelioration",
    "stabilise":        "stabilise",
}


def _header(title: str, width: int = 64) -> str:
    return f"\n{'=' * width}\n  {title}\n{'=' * width}"


def _section(title: str, width: int = 64) -> str:
    return f"\n{'-' * width}\n  {title}\n{'-' * width}"


def _display_item(idx: int, item: dict) -> None:
    src  = _SOURCE_ICON.get(item["source"], "[?]")
    diff = _DIFF_ICON.get(item["difficulty"], "(?)")
    print(f"  {idx:2d}. {src} [{item['priority']:.3f}] {diff}  "
          f"{item['question_type']:20s}  skill: {item['target_skill']}")
    print(f"       {item['reason']}")


def run(user_id: str) -> None:
    print(_header(f"Curriculum Observer -- user: {user_id}"))

    rec = get_curriculum_recommendation(user_id)
    queue  = rec["queue"]
    focus  = rec["focus"]
    nxt    = rec["next_step"]

    # ---- Prochaine etape ------------------------------------------------
    print(_section("Prochaine etape recommandee"))
    if nxt:
        src  = _SOURCE_ICON.get(nxt["source"], "[?]")
        diff = _DIFF_ICON.get(nxt["difficulty"], "(?)")
        print(f"  Source   : {nxt['source']}")
        print(f"  Skill    : {nxt['target_skill']}")
        print(f"  Type Q   : {nxt['question_type']}")
        print(f"  Difficulte: {nxt['difficulty']} {diff}")
        print(f"  Priorite : {nxt['priority']:.3f}")
        print(f"  Raison   : {nxt['reason']}")
    else:
        print("  (aucune etape disponible)")

    # ---- Queue complete --------------------------------------------------
    print(_section(f"Queue pedagogique ({len(queue)} items)"))
    if queue:
        print(f"  {'#':>3}  {'SRC':6}  {'PRIO':6}  {'D':3}  {'TYPE_QUESTION':20}  SKILL")
        print(f"  {'-'*60}")
        for i, item in enumerate(queue, 1):
            _display_item(i, item)
    else:
        print("  (queue vide)")

    # ---- Focus de revision ----------------------------------------------
    print(_section("Synthese focus de revision"))

    conf  = focus.get("confidence", "?")
    n_att = focus.get("n_attempts_total", 0)
    avg   = focus.get("avg_score")
    avg_s = f"{avg:.1%}" if avg is not None else "N/A"
    print(f"  Confiance     : {conf.upper()} ({n_att} tentatives total)")
    print(f"  Score recent  : {avg_s}")

    fragile = focus.get("fragile_skills", [])
    if fragile:
        print(f"\n  Skills fragiles ({len(fragile)}) :")
        for s in fragile:
            print(f"    - {s}")
    else:
        print("\n  Skills fragiles : aucun")

    active = focus.get("active_patterns", [])
    if active:
        print(f"\n  Patterns actifs ({len(active)}) :")
        for p in active:
            trend_lbl = _TREND_LABEL.get(p["trend"], p["trend"])
            print(f"    - [{trend_lbl}] {p['error_type']} "
                  f"({p['count']}x, score moy {p['avg_score']:.0%})")
    else:
        print("\n  Patterns actifs : aucun")

    rev = focus.get("revision_due")
    if rev:
        print(f"\n  Revision due : chunk #{rev['chunk_id']} "
              f"'{str(rev.get('section_label',''))[:40]}' "
              f"(score {float(rev.get('avg_score') or 0):.0%})")
    else:
        print("\n  Revision due : aucune")

    print(f"\n{'=' * 64}\n")


def main() -> None:
    user_id = sys.argv[1] if len(sys.argv) > 1 else "default"

    # Tentative de resolution user_id par username
    try:
        with __import__("sqlite3").connect(_db.DB_PATH) as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username=? LIMIT 1", (user_id,)
            ).fetchone()
            if row:
                user_id = row[0]
    except Exception:
        pass

    run(user_id)


if __name__ == "__main__":
    main()
