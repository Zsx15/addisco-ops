#!/usr/bin/env python
"""
chunk_quality_analyzer.py — Chunk Quality Analyzer V1 (TASK-054)

Analyse read-only la qualité pédagogique des chunks en base.

Usage (depuis la racine du projet) :
    python tools/observability/chunk_quality_analyzer.py
    python tools/observability/chunk_quality_analyzer.py --document_id 1
    python tools/observability/chunk_quality_analyzer.py --min_attempts 5

Read-only strict : aucune écriture SQL, aucun appel API, aucun fix automatique.
"""
import argparse
import os
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# ── Seuils ────────────────────────────────────────────────────────────────────
MIN_CHARS            = 80      # chunk trop court si < MIN_CHARS
MAX_CHARS            = 2000    # chunk trop long si > MAX_CHARS
OPTIMAL_MIN          = 150     # idéal minimum
OPTIMAL_MAX          = 800     # idéal maximum
MAX_SKILLS_PER_CHUNK = 6       # trop de skills si > MAX_SKILLS_PER_CHUNK
MIN_ATTEMPTS_QUALIFY = 3       # nb minimum d'attempts pour juger la qualité
WEAK_SCORE_THRESHOLD = 0.45    # avg_score < seuil + assez d'attempts = WEAK
NOISE_TABLE_LINE_RATIO = 0.25  # > 25 % de lignes tabulaires = NOISY
NOISE_NONALPHA_RATIO   = 0.45  # > 45 % de chars non-alpha = NOISY
DOC_FAIL_THRESHOLD   = 0.50    # avg_score doc < seuil = document problématique

DB_PATH = Path(os.getenv("DB_PATH", "database.db"))

SEP  = "-" * 76
SEP2 = "=" * 76

VERDICTS_ORDER = ["WEAK", "NOISY", "ORPHAN", "OVERSIZED", "UNDERSIZED", "WATCH", "OK"]


# ── Connexion read-only ───────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


# ── Détection de bruit ────────────────────────────────────────────────────────

def _is_noisy(text: str) -> tuple[bool, str]:
    """Détecte si un chunk est bruité (tabulaire, financier, liste de noms)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return False, ""

    # Ratio de lignes tabulaires (contenant | ou commençant par des chiffres/codes)
    table_lines = sum(
        1 for l in lines
        if "|" in l
        or re.match(r"^\s*[-–—]+\s*$", l)
        or re.match(r"^\s*\d{1,3}[.,]\d", l)
    )
    table_ratio = table_lines / len(lines)

    # Ratio de caractères non-alphabétiques (chiffres, symboles, ponctuation lourde)
    total_chars = len(text.replace(" ", "").replace("\n", ""))
    if total_chars == 0:
        return False, ""
    alpha_chars = sum(1 for c in text if c.isalpha())
    nonalpha_ratio = 1.0 - (alpha_chars / total_chars)

    reasons = []
    if table_ratio >= NOISE_TABLE_LINE_RATIO:
        reasons.append(f"tabulaire ({table_ratio:.0%} lignes)")
    if nonalpha_ratio >= NOISE_NONALPHA_RATIO:
        reasons.append(f"non-alpha ({nonalpha_ratio:.0%} chars)")

    return bool(reasons), " + ".join(reasons)


# ── Requêtes DB ───────────────────────────────────────────────────────────────

def _load_chunks(conn: sqlite3.Connection, document_id: Optional[int]) -> list:
    query = """
        SELECT c.id, c.document_id, c.chunk_index, c.section_title,
               c.char_count, c.chunk_text, d.title AS doc_title
        FROM   chunks c
        JOIN   documents d ON d.id = c.document_id
    """
    params: tuple = ()
    if document_id is not None:
        query += " WHERE c.document_id = ?"
        params = (document_id,)
    query += " ORDER BY c.document_id, c.chunk_index"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def _load_skills_per_chunk(conn: sqlite3.Connection) -> dict:
    """chunk_id → count de skills actifs associés."""
    rows = conn.execute("""
        SELECT chunk_id, COUNT(*) AS n
        FROM   chunk_skills
        WHERE  is_active = 1
        GROUP  BY chunk_id
    """).fetchall()
    return {r["chunk_id"]: r["n"] for r in rows}


def _load_attempts_per_chunk(conn: sqlite3.Connection,
                              min_attempts: int) -> dict:
    """chunk_id → {n_attempts, avg_score, n_errors}"""
    rows = conn.execute("""
        SELECT chunk_id,
               COUNT(*)        AS n_attempts,
               AVG(score)      AS avg_score,
               SUM(CASE WHEN score < 0.5 THEN 1 ELSE 0 END) AS n_errors
        FROM   attempts
        WHERE  chunk_id IS NOT NULL
        GROUP  BY chunk_id
    """).fetchall()
    return {
        r["chunk_id"]: {
            "n_attempts": r["n_attempts"],
            "avg_score":  round(r["avg_score"], 3) if r["avg_score"] is not None else None,
            "n_errors":   r["n_errors"],
        }
        for r in rows
    }


# ── Analyse d'un chunk ────────────────────────────────────────────────────────

def _analyze_chunk(chunk: dict, n_skills: int, attempts: Optional[dict],
                   min_attempts: int) -> dict:
    issues = []
    text       = chunk["chunk_text"] or ""
    char_count = chunk["char_count"] or len(text)

    # Taille
    if char_count < MIN_CHARS:
        issues.append("UNDERSIZED")
    elif char_count > MAX_CHARS:
        issues.append("OVERSIZED")
    elif char_count < OPTIMAL_MIN or char_count > OPTIMAL_MAX:
        issues.append("WATCH")

    # Bruit
    noisy, noise_reason = _is_noisy(text)
    if noisy:
        issues.append("NOISY")

    # Orphelin
    if n_skills == 0:
        issues.append("ORPHAN")

    # Taux d'échec
    if attempts and attempts["n_attempts"] >= min_attempts:
        if attempts["avg_score"] is not None and attempts["avg_score"] < WEAK_SCORE_THRESHOLD:
            issues.append("WEAK")

    # Verdict principal (priorité décroissante)
    primary = "OK"
    for v in VERDICTS_ORDER:
        if v in issues:
            primary = v
            break

    return {
        "id":           chunk["id"],
        "document_id":  chunk["document_id"],
        "doc_title":    chunk["doc_title"],
        "chunk_index":  chunk["chunk_index"],
        "section":      chunk["section_title"] or "",
        "char_count":   char_count,
        "n_skills":     n_skills,
        "n_attempts":   attempts["n_attempts"] if attempts else 0,
        "avg_score":    attempts["avg_score"] if attempts else None,
        "issues":       issues,
        "primary":      primary,
        "noise_reason": noise_reason,
        "preview":      text[:120].replace("\n", " "),
    }


# ── Helpers affichage ─────────────────────────────────────────────────────────

def _section(title: str) -> None:
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)


def _score_str(s: Optional[float]) -> str:
    return f"{s:.2f}" if s is not None else "  —  "


def _verdict_icon(v: str) -> str:
    return {
        "OK":         "[OK]  ",
        "WATCH":      "[~~]  ",
        "NOISY":      "[BRUIT]",
        "ORPHAN":     "[SKL0] ",
        "OVERSIZED":  "[LONG] ",
        "UNDERSIZED": "[COURT]",
        "WEAK":       "[FAIL] ",
    }.get(v, v)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk Quality Analyzer V1 — read-only."
    )
    parser.add_argument(
        "--document_id", type=int, default=None,
        help="Analyser un document précis (défaut : tous les documents)"
    )
    parser.add_argument(
        "--min_attempts", type=int, default=MIN_ATTEMPTS_QUALIFY,
        help=f"Nb minimum d'attempts pour juger la qualité (défaut : {MIN_ATTEMPTS_QUALIFY})"
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERREUR] Base introuvable : {DB_PATH}")
        sys.exit(1)

    conn         = _conn()
    chunks       = _load_chunks(conn, args.document_id)
    skills_map   = _load_skills_per_chunk(conn)
    attempts_map = _load_attempts_per_chunk(conn, args.min_attempts)
    conn.close()

    if not chunks:
        print("[INFO] Aucun chunk trouvé.")
        sys.exit(0)

    # ── Analyse ───────────────────────────────────────────────────────────────
    results = [
        _analyze_chunk(
            c,
            skills_map.get(c["id"], 0),
            attempts_map.get(c["id"]),
            args.min_attempts,
        )
        for c in chunks
    ]

    # Agrégation par verdict
    by_verdict: dict = defaultdict(list)
    for r in results:
        by_verdict[r["primary"]].append(r)

    # Agrégation par document
    by_doc: dict = defaultdict(lambda: {"title": "", "chunks": []})
    for r in results:
        by_doc[r["document_id"]]["title"] = r["doc_title"]
        by_doc[r["document_id"]]["chunks"].append(r)

    # ── En-tête ───────────────────────────────────────────────────────────────
    scope = f"document_id={args.document_id}" if args.document_id else "tous les documents"
    print(f"\n{SEP2}")
    print(f"  CHUNK QUALITY ANALYZER V1  —  TASK-054")
    print(f"  Scope      : {scope}")
    print(f"  Base       : {DB_PATH}")
    print(f"  Chunks     : {len(results)}")
    print(f"  Seuils     : MIN={MIN_CHARS}  MAX={MAX_CHARS}  WEAK_SCORE<{WEAK_SCORE_THRESHOLD}  MIN_ATT={args.min_attempts}")
    print(SEP2)

    n_ok      = len(by_verdict.get("OK", []))
    n_issues  = len(results) - n_ok
    pct_ok    = n_ok / len(results) * 100 if results else 0

    print(f"\n  Résumé : {n_ok}/{len(results)} chunks OK ({pct_ok:.1f}%)  —  {n_issues} chunk(s) avec problème(s)\n")
    for v in VERDICTS_ORDER:
        count = len(by_verdict.get(v, []))
        if count:
            bar = "█" * min(count, 30)
            print(f"  {_verdict_icon(v)}  {count:>4}  {bar}")

    # ── Sections par verdict (hors OK) ────────────────────────────────────────
    for v in VERDICTS_ORDER:
        group = by_verdict.get(v, [])
        if not group or v == "OK":
            continue

        _section(f"CHUNKS {v}  ({len(group)})")
        print(f"  {'ID':>5}  {'DOC':>4}  {'IDX':>4}  {'CHARS':>6}  {'SKL':>4}  {'ATT':>4}  {'AVG':>6}  SECTION / APERÇU")
        print(f"  {SEP}")
        for r in sorted(group, key=lambda x: (x["document_id"], x["chunk_index"])):
            tags = " ".join(r["issues"])
            avg  = _score_str(r["avg_score"])
            preview = r["preview"][:55]
            section = (r["section"][:20] + "…") if len(r["section"]) > 20 else r["section"]
            print(
                f"  {r['id']:>5}  {r['document_id']:>4}  {r['chunk_index']:>4}"
                f"  {r['char_count']:>6}  {r['n_skills']:>4}  {r['n_attempts']:>4}"
                f"  {avg:>6}  {section:<22}  {preview}"
            )
            if r["noise_reason"]:
                print(f"         └── bruit : {r['noise_reason']}")

    # ── Rapport par document ──────────────────────────────────────────────────
    _section("RAPPORT PAR DOCUMENT")
    print(f"  {'DOC_ID':>6}  {'CHUNKS':>6}  {'OK':>4}  {'ISSUES':>6}  {'AVG_SCORE':>9}  TITRE")
    print(f"  {SEP}")
    for doc_id, data in sorted(by_doc.items()):
        doc_chunks  = data["chunks"]
        doc_ok      = sum(1 for c in doc_chunks if c["primary"] == "OK")
        doc_issues  = len(doc_chunks) - doc_ok
        scores      = [c["avg_score"] for c in doc_chunks if c["avg_score"] is not None]
        doc_avg     = sum(scores) / len(scores) if scores else None
        flag        = " ⚠" if doc_avg is not None and doc_avg < DOC_FAIL_THRESHOLD else ""
        title       = data["title"][:45]
        print(
            f"  {doc_id:>6}  {len(doc_chunks):>6}  {doc_ok:>4}  {doc_issues:>6}"
            f"  {_score_str(doc_avg):>9}{flag}  {title}"
        )

    # ── Recommandations ───────────────────────────────────────────────────────
    _section("RECOMMANDATIONS")

    recs = []

    n_orphan = len(by_verdict.get("ORPHAN", []))
    if n_orphan:
        recs.append(f"[ORPHAN]    {n_orphan} chunk(s) sans skill → lancer remap_skills ou réviser le mapping keyword.")

    n_noisy = len(by_verdict.get("NOISY", []))
    if n_noisy:
        recs.append(f"[NOISY]     {n_noisy} chunk(s) bruités (tabulaires/financiers) → envisager un post-traitement du chunker ou une exclusion manuelle.")

    n_weak = len(by_verdict.get("WEAK", []))
    if n_weak:
        recs.append(f"[WEAK]      {n_weak} chunk(s) avec taux d'échec élevé → réviser le contenu source ou améliorer le contexte fourni au LLM.")

    n_over = len(by_verdict.get("OVERSIZED", []))
    if n_over:
        recs.append(f"[OVERSIZED] {n_over} chunk(s) trop longs (>{MAX_CHARS} chars) → re-découper le document avec un seuil plus bas.")

    n_under = len(by_verdict.get("UNDERSIZED", []))
    if n_under:
        recs.append(f"[UNDERSIZED]{n_under} chunk(s) trop courts (<{MIN_CHARS} chars) → fusionner avec le chunk adjacent ou exclure.")

    doc_fails = [
        (doc_id, data)
        for doc_id, data in by_doc.items()
        if (
            scores := [c["avg_score"] for c in data["chunks"] if c["avg_score"] is not None]
        ) and sum(scores) / len(scores) < DOC_FAIL_THRESHOLD
    ]
    if doc_fails:
        recs.append(f"[DOC FAIL]  {len(doc_fails)} document(s) avec score moyen < {DOC_FAIL_THRESHOLD} → réviser la qualité du document source.")

    if recs:
        for rec in recs:
            print(f"  {rec}")
    else:
        print("  Aucune recommandation critique.")

    # ── Verdict global ────────────────────────────────────────────────────────
    _section("VERDICT GLOBAL")

    critical = n_weak + n_noisy
    moderate = n_orphan + n_over + n_under

    if critical >= 10 or (critical / len(results) > 0.15 if results else False):
        verdict_global = "FAILED"
        detail = f"{critical} chunks critiques (WEAK+NOISY) sur {len(results)} ({critical/len(results):.0%})"
    elif critical > 0 or moderate > 5:
        verdict_global = "GO WITH WARNING"
        detail = f"{critical} critiques, {moderate} modérés sur {len(results)} chunks"
    else:
        verdict_global = "GO SAFE"
        detail = f"corpus propre — {n_ok}/{len(results)} chunks OK"

    icon = {"GO SAFE": "✅", "GO WITH WARNING": "⚠️ ", "FAILED": "❌"}.get(verdict_global, "")
    print(f"\n  {icon}  {verdict_global}")
    print(f"      {detail}\n")
    print(SEP2 + "\n")


if __name__ == "__main__":
    main()
