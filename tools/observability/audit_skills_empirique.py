#!/usr/bin/env python
"""
audit_skills_empirique.py — Analyse empirique read-only des skills.

Usage (depuis la racine du projet) :
    python tools/observability/audit_skills_empirique.py --username test

Read-only strict : aucune écriture SQL, aucun appel API, aucun remap.
"""
import argparse
import os
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

# Force UTF-8 on Windows consoles (CP1252 rejects many Unicode chars).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# ── Seuils ────────────────────────────────────────────────────────────────────
COVERAGE_HIGH_PCT   = 40.0   # polluant si skill couvre ≥ 40 % des chunks
COVERAGE_LOW_CHUNKS = 5      # trop étroit si skill couvre < 5 chunks
MIN_ATTEMPTS_KEEP   = 10     # nb min d'attempts pour qualifier KEEP
DISCRIMINATION_DELTA = 0.05  # |mastery − avg| ≥ delta → discriminant
COLLISION_MIN       = 5      # co-occurrences min pour pattern émergent

DB_PATH = Path(os.getenv("DB_PATH", "database.db"))

SEP  = "-" * 74
SEP2 = "=" * 74


# ── Connexion read-only ───────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


# ── Requêtes ──────────────────────────────────────────────────────────────────

def _total_chunks(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def _all_skills(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT id, slug, label_fr, is_active FROM skills ORDER BY slug"
    ).fetchall()
    return [dict(r) for r in rows]


def _chunk_skills_stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("""
        SELECT s.slug,
               COUNT(DISTINCT cs.chunk_id)   AS n_chunks,
               COUNT(DISTINCT c.document_id) AS n_docs
        FROM   skills s
        LEFT JOIN chunk_skills cs ON cs.skill_id = s.id AND cs.is_active = 1
        LEFT JOIN chunks c        ON c.id = cs.chunk_id
        GROUP BY s.id, s.slug
    """).fetchall()
    return {r["slug"]: dict(r) for r in rows}


def _user_mastery(conn: sqlite3.Connection, user_id: str) -> dict:
    rows = conn.execute("""
        SELECT s.slug, usm.mastery_score, usm.attempts_count
        FROM   user_skill_mastery usm
        JOIN   skills s ON s.id = usm.skill_id
        WHERE  usm.user_id = ?
    """, (user_id,)).fetchall()
    return {r["slug"]: dict(r) for r in rows}


def _attempts_by_skill(conn: sqlite3.Connection, user_id: str) -> dict:
    rows = conn.execute("""
        SELECT s.slug, a.score, a.error_type
        FROM   attempts a
        JOIN   chunks c      ON c.id = a.chunk_id
        JOIN   chunk_skills cs ON cs.chunk_id = c.id AND cs.is_active = 1
        JOIN   skills s      ON s.id = cs.skill_id
        WHERE  a.user_id = ?
    """, (user_id,)).fetchall()
    result: dict = defaultdict(lambda: {"scores": [], "error_types": []})
    for r in rows:
        result[r["slug"]]["scores"].append(r["score"])
        if r["error_type"]:
            result[r["slug"]]["error_types"].append(r["error_type"])
    return dict(result)


def _collision_pairs(conn: sqlite3.Connection) -> list:
    rows = conn.execute("""
        SELECT cs1.skill_id AS s1, cs2.skill_id AS s2, COUNT(*) AS n
        FROM   chunk_skills cs1
        JOIN   chunk_skills cs2
               ON  cs1.chunk_id = cs2.chunk_id
               AND cs1.skill_id < cs2.skill_id
        WHERE  cs1.is_active = 1 AND cs2.is_active = 1
        GROUP  BY cs1.skill_id, cs2.skill_id
        HAVING n >= ?
        ORDER  BY n DESC
    """, (COLLISION_MIN,)).fetchall()
    return [dict(r) for r in rows]


def _skill_id_to_slug(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("SELECT id, slug FROM skills").fetchall()
    return {r["id"]: r["slug"] for r in rows}


def _doc_concentration(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("""
        SELECT s.slug, c.document_id, COUNT(*) AS n
        FROM   chunk_skills cs
        JOIN   skills s ON s.id  = cs.skill_id
        JOIN   chunks c ON c.id  = cs.chunk_id
        WHERE  cs.is_active = 1
        GROUP  BY s.slug, c.document_id
    """).fetchall()
    result: dict = defaultdict(list)
    for r in rows:
        result[r["slug"]].append({"doc_id": r["document_id"], "n": r["n"]})
    return dict(result)


# ── Verdict ───────────────────────────────────────────────────────────────────

def _verdict(n_chunks: int, total_chunks: int, mastery: Optional[float],
             global_avg: float, attempts_count: int) -> str:
    if n_chunks == 0 or attempts_count == 0:
        return "REMOVE/REWORK"
    cov_pct = n_chunks / total_chunks * 100 if total_chunks else 0
    if cov_pct >= COVERAGE_HIGH_PCT:
        return "REFINE"
    if n_chunks < COVERAGE_LOW_CHUNKS:
        return "REFINE"
    if attempts_count >= MIN_ATTEMPTS_KEEP:
        if mastery is not None and abs(mastery - global_avg) >= DISCRIMINATION_DELTA:
            return "KEEP"
        return "WATCH"
    return "WATCH"


# ── Helpers d'affichage ───────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)


def _m(mastery: Optional[float]) -> str:
    return f"{mastery:.3f}" if mastery is not None else "   —   "


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit empirique read-only des skills."
    )
    parser.add_argument("--username", required=True, help="Username cible (ex: test)")
    args = parser.parse_args()

    conn = _conn()

    row = conn.execute(
        "SELECT user_id FROM users WHERE username = ?", (args.username,)
    ).fetchone()
    if not row:
        print(f"[ERREUR] Utilisateur '{args.username}' introuvable dans la base.")
        conn.close()
        return
    user_id: str = row["user_id"]

    print(f"\n{SEP2}")
    print(f"  AUDIT EMPIRIQUE DES SKILLS")
    print(f"  Utilisateur : {args.username}  ({user_id})")
    print(f"  Base        : {DB_PATH}")
    print(SEP2)

    total_chunks = _total_chunks(conn)
    skills       = _all_skills(conn)
    chunk_stats  = _chunk_skills_stats(conn)
    mastery_data = _user_mastery(conn, user_id)
    attempts_by  = _attempts_by_skill(conn, user_id)
    id_to_slug   = _skill_id_to_slug(conn)
    doc_dist     = _doc_concentration(conn)

    print(f"\n  {total_chunks} chunks  ·  {len(skills)} skills dans la base")

    all_mastery = [v["mastery_score"] for v in mastery_data.values()]
    global_avg  = statistics.mean(all_mastery) if all_mastery else 0.0

    # ── Classifier tous les skills ────────────────────────────────────────────
    vivants:      list = []
    morts:        list = []
    discriminants: list = []
    polluants:    list = []
    etroits:      list = []

    for sk in skills:
        slug     = sk["slug"]
        cs       = chunk_stats.get(slug, {"n_chunks": 0, "n_docs": 0})
        n_chunks = cs["n_chunks"] or 0
        n_docs   = cs["n_docs"]   or 0
        cov_pct  = n_chunks / total_chunks * 100 if total_chunks else 0

        m_row    = mastery_data.get(slug, {})
        mastery  = m_row.get("mastery_score")
        att_cnt  = int(m_row.get("attempts_count") or 0)

        v = _verdict(n_chunks, total_chunks, mastery, global_avg, att_cnt)

        rec = {
            "slug":     slug,
            "label":    sk["label_fr"],
            "n_chunks": n_chunks,
            "n_docs":   n_docs,
            "cov_pct":  round(cov_pct, 1),
            "mastery":  mastery,
            "attempts": att_cnt,
            "verdict":  v,
        }

        if n_chunks == 0 or att_cnt == 0:
            morts.append(rec)
        else:
            vivants.append(rec)
            if cov_pct >= COVERAGE_HIGH_PCT:
                polluants.append(rec)
            if n_chunks < COVERAGE_LOW_CHUNKS:
                etroits.append(rec)
            if (att_cnt >= MIN_ATTEMPTS_KEEP
                    and mastery is not None
                    and abs(mastery - global_avg) >= DISCRIMINATION_DELTA):
                discriminants.append(rec)

    # ═══════════ 1. SKILLS VIVANTS ═══════════════════════════════════════════
    _section("1. SKILLS VIVANTS")
    hdr = f"{'SLUG':<35} {'CHUNKS':>7} {'DOCS':>5} {'COV%':>6} {'MASTERY':>8} {'ATT':>6}  VERDICT"
    print(hdr)
    print(SEP)
    for r in sorted(vivants, key=lambda x: -x["n_chunks"]):
        print(
            f"{r['slug']:<35} {r['n_chunks']:>7} {r['n_docs']:>5}"
            f" {r['cov_pct']:>5.1f}% {_m(r['mastery']):>8} {r['attempts']:>6}  {r['verdict']}"
        )

    # ═══════════ 2. SKILLS MORTS ═════════════════════════════════════════════
    _section("2. SKILLS MORTS  (aucune détection ou aucun attempt)")
    if morts:
        print(f"{'SLUG':<35} {'CHUNKS':>7} {'ATT':>6}  VERDICT")
        print(SEP)
        for r in morts:
            print(f"{r['slug']:<35} {r['n_chunks']:>7} {r['attempts']:>6}  {r['verdict']}")
    else:
        print("  Aucun skill mort.")

    # ═══════════ 3. SKILLS DISCRIMINANTS ═════════════════════════════════════
    _section(
        f"3. SKILLS DISCRIMINANTS  "
        f"(>= {MIN_ATTEMPTS_KEEP} attempts  |mastery - avg| >= {DISCRIMINATION_DELTA})"
    )
    print(f"  Moyenne globale mastery : {global_avg:.3f}")
    if discriminants:
        print(f"\n{'SLUG':<35} {'MASTERY':>8} {'DELTA':>8} {'ATT':>6}")
        print(SEP)
        for r in sorted(discriminants, key=lambda x: -abs((x["mastery"] or 0) - global_avg)):
            delta = (r["mastery"] or 0) - global_avg
            print(f"{r['slug']:<35} {r['mastery']:>8.3f} {delta:>+8.3f} {r['attempts']:>6}")
    else:
        print("  Aucun skill discriminant (delta insuffisant ou trop peu d'attempts).")

    # ═══════════ 4. SKILLS POLLUANTS ═════════════════════════════════════════
    _section(f"4. SKILLS POLLUANTS  (couverture ≥ {COVERAGE_HIGH_PCT:.0f} % des chunks)")
    if polluants:
        print(f"{'SLUG':<35} {'CHUNKS':>7} {'COV%':>6}  DIAGNOSTIC")
        print(SEP)
        for r in polluants:
            print(f"{r['slug']:<35} {r['n_chunks']:>7} {r['cov_pct']:>5.1f}%  trop large → REFINE")
    else:
        print(f"  Aucun skill polluant (tous < {COVERAGE_HIGH_PCT:.0f} %).")

    # ═══════════ 5. PATTERNS ÉMERGENTS ═══════════════════════════════════════
    _section("5. PATTERNS ÉMERGENTS")

    # 5a — Co-occurrences
    pairs = _collision_pairs(conn)
    print(f"\n5a. Co-occurrences de skills sur les memes chunks (>= {COLLISION_MIN}) :")
    if pairs:
        print(f"{'SKILL A':<35} {'SKILL B':<35} {'CO-OCC':>7}")
        print(SEP)
        for p in pairs[:15]:
            s1 = id_to_slug.get(p["s1"], str(p["s1"]))
            s2 = id_to_slug.get(p["s2"], str(p["s2"]))
            print(f"{s1:<35} {s2:<35} {p['n']:>7}")
    else:
        print("  Aucune co-occurrence significative.")

    # 5b — Skills trop étroits
    print(f"\n5b. Skills trop etroits (< {COVERAGE_LOW_CHUNKS} chunks) :")
    if etroits:
        for r in etroits:
            print(f"  {r['slug']:<35}  {r['n_chunks']} chunk(s)  →  REFINE")
    else:
        print(f"  Aucun skill < {COVERAGE_LOW_CHUNKS} chunks.")

    # 5c — Concentration documentaire
    print("\n5c. Concentration documentaire (skill présent sur un seul doc) :")
    concentrated = [
        (slug, dlist[0]["doc_id"], dlist[0]["n"])
        for slug, dlist in doc_dist.items()
        if len(dlist) == 1
    ]
    if concentrated:
        print(f"  {'SLUG':<35} {'DOC_ID':>8} {'CHUNKS':>7}")
        for slug, doc_id, n in sorted(concentrated, key=lambda x: -x[2]):
            print(f"  {slug:<35} {doc_id:>8} {n:>7}")
    else:
        print("  Aucun skill concentré sur un seul document.")

    # 5d — Error types
    print("\n5d. Types d'erreurs fréquents par skill (top 3) :")
    found_errors = False
    for slug in sorted(attempts_by):
        errs = Counter(attempts_by[slug]["error_types"])
        if errs:
            found_errors = True
            top_str = "  ".join(f"{e}({n})" for e, n in errs.most_common(3))
            print(f"  {slug:<35}  {top_str}")
    if not found_errors:
        print("  Aucune donnée error_type disponible.")

    # ═══════════ 6. RAPPORT FINAL ════════════════════════════════════════════
    _section("6. RAPPORT FINAL — TABLEAU RÉCAPITULATIF")
    print(f"{'SLUG':<35} {'CHUNKS':>7} {'COV%':>6} {'MASTERY':>8} {'ATT':>6}  VERDICT")
    print(SEP)
    all_recs = vivants + morts
    for r in sorted(all_recs, key=lambda x: (x["verdict"], -x["n_chunks"])):
        print(
            f"{r['slug']:<35} {r['n_chunks']:>7} {r['cov_pct']:>5.1f}%"
            f" {_m(r['mastery']):>8} {r['attempts']:>6}  {r['verdict']}"
        )

    # ═══════════ 7. VERDICT PAR SKILL ════════════════════════════════════════
    _section("7. VERDICT PAR SKILL")
    icons     = {"KEEP": "[OK]", "WATCH": "[??]", "REFINE": "[~]", "REMOVE/REWORK": "[X]"}
    summaries = {"KEEP": [], "WATCH": [], "REFINE": [], "REMOVE/REWORK": []}
    for r in all_recs:
        summaries[r["verdict"]].append(r)

    for label in ("KEEP", "WATCH", "REFINE", "REMOVE/REWORK"):
        group = summaries[label]
        icon  = icons[label]
        print(f"\n  {icon} {label} ({len(group)} skill{'s' if len(group) != 1 else ''}) :")
        if group:
            for r in sorted(group, key=lambda x: -x["n_chunks"]):
                tags = []
                if r["cov_pct"] >= COVERAGE_HIGH_PCT:
                    tags.append("polluant")
                if 0 < r["n_chunks"] < COVERAGE_LOW_CHUNKS:
                    tags.append("trop étroit")
                if r["n_chunks"] == 0:
                    tags.append("aucun chunk")
                if r["attempts"] == 0:
                    tags.append("aucun attempt")
                tag_str = f"  [{', '.join(tags)}]" if tags else ""
                m_str   = f"mastery={r['mastery']:.3f}" if r["mastery"] is not None else "mastery=—"
                print(f"    - {r['slug']:<35}  {m_str}  att={r['attempts']}{tag_str}")
        else:
            print("    (aucun)")

    print(f"\n{SEP2}")
    print(f"  Audit terminé.")
    print(SEP2 + "\n")

    conn.close()


if __name__ == "__main__":
    main()
