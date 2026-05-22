#!/usr/bin/env python
"""
maintenance_report.py — Maintenance Assistée V1 (TASK-060)

Rapport de maintenance pédagogique et structurelle.
Agrège : chunks, skills, documents, dérives de scores, anomalies attempts, guardrails.

Usage :
    python tools/maintenance/maintenance_report.py
    python tools/maintenance/maintenance_report.py --min_attempts 5

Read-only strict : aucune écriture SQL, aucun appel API, aucun fix automatique.
Verdict final : GO SAFE / WARNING / FAILED
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", "database.db"))

# ── Seuils ─────────────────────────────────────────────────────────────────────
MIN_ATTEMPTS_QUALIFY  = 3      # nb minimum d'attempts pour juger un chunk / doc
DOC_FAIL_THRESHOLD    = 0.45   # avg_score doc < seuil → problématique
DRIFT_THRESHOLD       = 0.20   # delta score global vs 7 derniers jours → dérive
STREAK_ZERO_THRESHOLD = 5      # N tentatives score=0 consécutives → anomalie
FAST_RESPONSE_SEC     = 5      # réponse < N secondes → suspicieux
MAX_SKILLS_PER_CHUNK  = 6      # skill avec trop de chunks associés
PCT_CHUNKS_CRITICAL   = 30     # % chunks problématiques → verdict FAILED

SEP  = "-" * 72
SEP2 = "=" * 72


# ── DB ─────────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


# ── Affichage ──────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def _ok(msg: str)   -> None: print(f"  OK  {msg}")
def _warn(msg: str) -> None: print(f"  !!  {msg}")
def _crit(msg: str) -> None: print(f"  XX  {msg}")


# ── 1. Chunks ──────────────────────────────────────────────────────────────────

def _analyze_chunks(conn: sqlite3.Connection, min_attempts: int) -> dict:
    from tools.observability.chunk_quality_analyzer import (
        _load_chunks,
        _load_skills_per_chunk,
        _load_attempts_per_chunk,
        _analyze_chunk,
    )
    chunks       = _load_chunks(conn, None)
    skills_map   = _load_skills_per_chunk(conn)
    attempts_map = _load_attempts_per_chunk(conn, min_attempts)

    results = [
        _analyze_chunk(
            c,
            skills_map.get(c["id"], 0),
            attempts_map.get(c["id"]),
            min_attempts,
        )
        for c in chunks
    ]
    return {
        "total":    len(results),
        "weak":     [r for r in results if "WEAK"      in r["issues"]],
        "noisy":    [r for r in results if "NOISY"     in r["issues"]],
        "orphan":   [r for r in results if "ORPHAN"    in r["issues"]],
        "oversized":[r for r in results if "OVERSIZED" in r["issues"]],
    }


# ── 2. Skills ──────────────────────────────────────────────────────────────────

def _analyze_skills(conn: sqlite3.Connection) -> dict:
    all_skills = {
        r["id"]: {"slug": r["slug"], "label": r["label_fr"]}
        for r in conn.execute(
            "SELECT id, slug, label_fr FROM skills WHERE is_active = 1"
        ).fetchall()
    }

    active_ids = {
        r["skill_id"]
        for r in conn.execute(
            "SELECT DISTINCT skill_id FROM chunk_skills WHERE is_active = 1"
        ).fetchall()
    }
    mastery_ids = {
        r["skill_id"]
        for r in conn.execute(
            "SELECT DISTINCT skill_id FROM user_skill_mastery"
        ).fetchall()
    }

    dead = [
        all_skills[sid]
        for sid in all_skills
        if sid not in active_ids and sid not in mastery_ids
    ]

    oversized = conn.execute("""
        SELECT s.slug, s.label_fr, COUNT(*) AS n
        FROM   chunk_skills cs
        JOIN   skills s ON s.id = cs.skill_id
        WHERE  cs.is_active = 1
        GROUP  BY cs.skill_id
        HAVING n > ?
        ORDER  BY n DESC
    """, (MAX_SKILLS_PER_CHUNK,)).fetchall()

    return {
        "total":    len(all_skills),
        "dead":     dead,
        "oversized": [(r["slug"], r["label_fr"], r["n"]) for r in oversized],
    }


# ── 3. Documents ───────────────────────────────────────────────────────────────

def _analyze_documents(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("""
        SELECT d.id, d.title,
               COUNT(a.id)  AS n_attempts,
               AVG(a.score) AS avg_score
        FROM   documents d
        LEFT   JOIN chunks  c ON c.document_id = d.id
        LEFT   JOIN attempts a ON a.chunk_id   = c.id
        GROUP  BY d.id, d.title
        ORDER  BY avg_score ASC NULLS LAST
    """).fetchall()

    docs = [dict(r) for r in rows]
    problematic = [
        d for d in docs
        if d["n_attempts"] >= MIN_ATTEMPTS_QUALIFY
        and d["avg_score"] is not None
        and d["avg_score"] < DOC_FAIL_THRESHOLD
    ]
    no_attempts = [d for d in docs if d["n_attempts"] == 0]

    return {
        "total":       len(docs),
        "problematic": problematic,
        "no_attempts": no_attempts,
    }


# ── 4. Dérive de scores ────────────────────────────────────────────────────────

def _analyze_score_drift(conn: sqlite3.Connection) -> dict:
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()

    global_rows = conn.execute("""
        SELECT user_id, AVG(score) AS avg_global, COUNT(*) AS n_total
        FROM   attempts
        GROUP  BY user_id
        HAVING n_total >= ?
    """, (MIN_ATTEMPTS_QUALIFY,)).fetchall()

    drifting = []
    for row in global_rows:
        recent = conn.execute("""
            SELECT AVG(score) AS avg_recent, COUNT(*) AS n_recent
            FROM   attempts
            WHERE  user_id = ? AND created_at >= ?
        """, (row["user_id"], cutoff)).fetchone()

        if (
            recent
            and recent["n_recent"] >= 3
            and recent["avg_recent"] is not None
        ):
            delta = row["avg_global"] - recent["avg_recent"]
            if delta > DRIFT_THRESHOLD:
                drifting.append({
                    "user_id":    row["user_id"],
                    "avg_global": row["avg_global"],
                    "avg_recent": recent["avg_recent"],
                    "delta":      delta,
                })

    return {"drifting": drifting}


# ── 5. Anomalies attempts ──────────────────────────────────────────────────────

def _analyze_anomalies(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) AS n FROM attempts").fetchone()["n"]

    fast = conn.execute("""
        SELECT COUNT(*) AS n FROM attempts
        WHERE  response_time_seconds IS NOT NULL
          AND  response_time_seconds > 0
          AND  response_time_seconds < ?
    """, (FAST_RESPONSE_SEC,)).fetchone()["n"]

    non_eval = conn.execute("""
        SELECT COUNT(*) AS n FROM attempts
        WHERE  error_type = 'non_evaluable'
    """).fetchone()["n"]

    # Streaks de score 0 par utilisateur
    users = [
        r["user_id"]
        for r in conn.execute("SELECT DISTINCT user_id FROM attempts").fetchall()
    ]
    streaks = []
    for uid in users:
        scores = [
            r["score"]
            for r in conn.execute(
                "SELECT score FROM attempts WHERE user_id = ? ORDER BY created_at ASC",
                (uid,),
            ).fetchall()
            if r["score"] is not None
        ]
        max_streak = cur = 0
        for s in scores:
            if s == 0.0:
                cur += 1
                max_streak = max(max_streak, cur)
            else:
                cur = 0
        if max_streak >= STREAK_ZERO_THRESHOLD:
            streaks.append({"user_id": uid, "streak": max_streak})

    return {
        "total":    total,
        "fast":     fast,
        "non_eval": non_eval,
        "streaks":  streaks,
    }


# ── 6. Guardrails ──────────────────────────────────────────────────────────────

def _analyze_guardrails() -> dict:
    from tools.guardrails.architecture_guardrails import (
        check_file_sizes,
        check_function_lengths,
        check_dangerous_imports,
        check_sql_without_limit,
        check_secrets,
        check_streamlit_heavy,
    )
    findings = (
        check_file_sizes(ROOT)
        + check_function_lengths(ROOT)
        + check_dangerous_imports(ROOT)
        + check_sql_without_limit(ROOT)
        + check_secrets(ROOT)
        + check_streamlit_heavy(ROOT)
    )
    return {
        "critical": [f for f in findings if f.level == "CRITICAL"],
        "warning":  [f for f in findings if f.level == "WARNING"],
        "total":    len(findings),
    }


# ── Rapport principal ──────────────────────────────────────────────────────────

def run_maintenance_report(min_attempts: int = MIN_ATTEMPTS_QUALIFY) -> int:
    """
    Lance le rapport complet.
    Retourne : 0 = GO SAFE, 1 = WARNING, 2 = FAILED.
    """
    if not DB_PATH.exists():
        print(f"[ERREUR] Base introuvable : {DB_PATH}")
        return 2

    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _conn()

    print(f"\n{SEP2}")
    print(f"  MAINTENANCE REPORT V1  —  TASK-060")
    print(f"  Date   : {ts}")
    print(f"  Base   : {DB_PATH}")
    print(SEP2)

    issues_warning:  list[str] = []
    issues_critical: list[str] = []

    # ── 1. Chunks ──────────────────────────────────────────────────────────────
    _header("1 / CHUNKS")
    chunks = _analyze_chunks(conn, min_attempts)

    if chunks["total"] == 0:
        _warn("Aucun chunk en base.")
        issues_warning.append("Aucun chunk en base")
    else:
        n_issues = len(chunks["weak"]) + len(chunks["noisy"]) + len(chunks["orphan"])
        pct = n_issues / chunks["total"] * 100
        print(f"  Total : {chunks['total']}  —  problèmes : {n_issues} ({pct:.1f}%)")

        if chunks["weak"]:
            for r in chunks["weak"][:5]:
                _warn(f"WEAK    chunk#{r['id']}  {r['doc_title'][:30]}  avg={r['avg_score']:.2f}")
            if len(chunks["weak"]) > 5:
                print(f"         ... et {len(chunks['weak']) - 5} autres chunks WEAK")
            issues_warning.append(f"{len(chunks['weak'])} chunk(s) WEAK")

        if chunks["orphan"]:
            _warn(f"{len(chunks['orphan'])} chunk(s) ORPHAN (aucun skill associé)")
            issues_warning.append(f"{len(chunks['orphan'])} chunk(s) ORPHAN")

        if chunks["noisy"]:
            _warn(f"{len(chunks['noisy'])} chunk(s) NOISY (tabulaire / non-alpha)")
            issues_warning.append(f"{len(chunks['noisy'])} chunk(s) NOISY")

        if pct >= PCT_CHUNKS_CRITICAL:
            issues_critical.append(f"{pct:.0f}% chunks avec problèmes (seuil : {PCT_CHUNKS_CRITICAL}%)")

        if n_issues == 0:
            _ok(f"Tous les chunks ({chunks['total']}) sont sains.")

    # ── 2. Skills ──────────────────────────────────────────────────────────────
    _header("2 / SKILLS")
    skills = _analyze_skills(conn)
    print(f"  Total skills actifs en base : {skills['total']}")

    if skills["dead"]:
        for s in skills["dead"][:10]:
            _warn(f"MORT    {s['slug']}  ({s['label']})")
        if len(skills["dead"]) > 10:
            print(f"         ... et {len(skills['dead']) - 10} autres")
        issues_warning.append(f"{len(skills['dead'])} skill(s) mort(s)")
    else:
        _ok("Aucun skill mort détecté.")

    if skills["oversized"]:
        for slug, label, n in skills["oversized"][:5]:
            _warn(f"LARGE   {slug}  ({label})  →  {n} chunks")
        issues_warning.append(f"{len(skills['oversized'])} skill(s) surchargé(s)")
    else:
        _ok(f"Aucun skill surchargé (> {MAX_SKILLS_PER_CHUNK} chunks).")

    # ── 3. Documents ───────────────────────────────────────────────────────────
    _header("3 / DOCUMENTS")
    docs = _analyze_documents(conn)
    print(f"  Total documents : {docs['total']}")

    if docs["problematic"]:
        for d in docs["problematic"]:
            _warn(
                f"FAIL    {d['title'][:45]}  "
                f"avg={d['avg_score']:.2f}  ({d['n_attempts']} att.)"
            )
        issues_warning.append(f"{len(docs['problematic'])} document(s) problématique(s)")
    else:
        _ok("Aucun document avec taux d'échec critique.")

    if docs["no_attempts"]:
        for d in docs["no_attempts"][:5]:
            print(f"  --    jamais utilisé : {d['title'][:55]}")
        if len(docs["no_attempts"]) > 5:
            print(f"         ... et {len(docs['no_attempts']) - 5} autres")

    # ── 4. Dérive de scores ────────────────────────────────────────────────────
    _header("4 / DÉRIVE DE SCORES  (7 derniers jours vs historique global)")
    drift = _analyze_score_drift(conn)

    if drift["drifting"]:
        for d in drift["drifting"]:
            _warn(
                f"DRIFT   {d['user_id'][:20]}  "
                f"global={d['avg_global']:.2f}  "
                f"récent={d['avg_recent']:.2f}  "
                f"delta=-{d['delta']:.2f}"
            )
        if any(d["delta"] > 0.40 for d in drift["drifting"]):
            issues_critical.append("Dérive de score sévère (> 40 points)")
        else:
            issues_warning.append(f"{len(drift['drifting'])} utilisateur(s) en dérive de score")
    else:
        _ok("Aucune dérive de score détectée.")

    # ── 5. Anomalies attempts ──────────────────────────────────────────────────
    _header("5 / ANOMALIES ATTEMPTS")
    anomalies = _analyze_anomalies(conn)
    print(f"  Total attempts : {anomalies['total']}")

    if anomalies["non_eval"] > 0 and anomalies["total"] > 0:
        pct_ne = anomalies["non_eval"] / anomalies["total"] * 100
        msg = f"{anomalies['non_eval']} tentatives non-évaluables ({pct_ne:.1f}%)"
        if pct_ne > 20:
            _warn(msg)
            issues_warning.append(msg)
        else:
            print(f"  --    {msg}")

    if anomalies["fast"] > 0 and anomalies["total"] > 0:
        pct_f = anomalies["fast"] / anomalies["total"] * 100
        msg = f"{anomalies['fast']} réponses très rapides (< {FAST_RESPONSE_SEC}s)  ({pct_f:.1f}%)"
        if pct_f > 15:
            _warn(msg)
            issues_warning.append(msg)
        else:
            print(f"  --    {msg}")

    if anomalies["streaks"]:
        for s in anomalies["streaks"]:
            _warn(f"STREAK  {s['user_id'][:25]}  {s['streak']} réponses nulles consécutives")
        issues_warning.append(f"{len(anomalies['streaks'])} utilisateur(s) avec streak score=0")
    else:
        _ok("Aucun streak de score nul détecté.")

    if anomalies["total"] == 0:
        print("  --    Aucune tentative en base.")

    conn.close()

    # ── 6. Guardrails ──────────────────────────────────────────────────────────
    _header("6 / GUARDRAILS ARCHITECTURE")
    guardrails = _analyze_guardrails()
    print(f"  CRITICAL : {len(guardrails['critical'])}  —  WARNING : {len(guardrails['warning'])}")

    for f in guardrails["critical"][:5]:
        _crit(f"[{f.rule}] {f.file} → {f.message}")
    for f in guardrails["warning"][:5]:
        _warn(f"[{f.rule}] {f.file} → {f.message}")

    if guardrails["total"] > 10:
        remaining = guardrails["total"] - 10
        print(
            f"  ... {remaining} finding(s) supplémentaire(s) — "
            "relancer tools/guardrails/architecture_guardrails.py pour le détail"
        )

    if guardrails["critical"]:
        issues_critical.extend(
            f"Guardrail CRITICAL [{f.rule}] {f.file}"
            for f in guardrails["critical"][:3]
        )
    if guardrails["warning"]:
        issues_warning.append(f"{len(guardrails['warning'])} finding(s) guardrails WARNING")

    if guardrails["total"] == 0:
        _ok("Aucune anomalie guardrails.")

    # ── Synthèse ───────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print(f"  SYNTHÈSE")
    print(SEP2)

    if issues_critical:
        print("\n  CRITIQUE :")
        for iss in issues_critical:
            _crit(iss)

    if issues_warning:
        print("\n  ATTENTION :")
        for iss in issues_warning:
            _warn(iss)

    if not issues_critical and not issues_warning:
        print("\n  Aucune anomalie détectée — moteur sain.")

    if issues_critical:
        verdict, code = "FAILED", 2
    elif issues_warning:
        verdict, code = "WARNING", 1
    else:
        verdict, code = "GO SAFE", 0

    print(f"\n{SEP2}")
    print(f"  VERDICT : {verdict}")
    print(f"{SEP2}\n")

    return code


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Maintenance Assistée V1 — rapport pédagogique et structurel read-only."
    )
    parser.add_argument(
        "--min_attempts",
        type=int,
        default=MIN_ATTEMPTS_QUALIFY,
        help=f"Nb minimum d'attempts pour juger un chunk (défaut : {MIN_ATTEMPTS_QUALIFY})",
    )
    args = parser.parse_args()
    sys.exit(run_maintenance_report(args.min_attempts))


if __name__ == "__main__":
    main()
