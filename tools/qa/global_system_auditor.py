"""
Global System Auditor — ADDISCO OPS
Audit read-only complet : structure, DB, corpus, learning data, chunks, skills,
runtime, calibration, sécurité, tests.

Usage :
    python tools/qa/global_system_auditor.py
    python tools/qa/global_system_auditor.py --run-tests
    python tools/qa/global_system_auditor.py --verbose --check-calibration
    python tools/qa/global_system_auditor.py --json
    python tools/qa/global_system_auditor.py --fail-on-warning
"""
from __future__ import annotations

import argparse
import json
import os
import py_compile
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

# ── Racine du projet ──────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

# Forcer UTF-8 sur Windows (CP1252 incompatible avec les caractères box-drawing)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DB_PATH = Path(os.getenv("DB_PATH", str(_ROOT / "database.db")))
REPORTS_DIR = _ROOT / "reports"

# ── Constantes attendues ──────────────────────────────────────────────────────
_EXPECTED_TABLES = [
    "attempts", "documents", "chunks", "users", "user_learning_profile",
    "skills", "chunk_skills", "user_skill_mastery", "runtime_metrics",
    "corpus", "corpus_documents",
]

_EXPECTED_SKILLS = [
    "memorisation_faits", "comprehension_procedure", "identification_concepts",
    "application_regles", "analyse_causale", "resolution_problemes",
    "prise_decision", "evaluation_critique", "synthese_reformulation",
    "conformite_reglementaire",
]

_KNOWN_ERROR_TYPES = {
    "correct", "reponse_vague", "oubli_etape", "hors_sujet",
    "non_evaluable", "erreur_logique", "erreur_factuelle",
    "incomplet", "mauvaise_interpretation",
}

_KNOWN_QUESTION_TYPES = {
    "question_directe", "cas_pratique", "vrai_faux",
    "question_piege", "reformulation", "consequence",
}

_KEY_FILES = [
    "app.py", "database.py", "ai_service.py", "document_service.py",
    "adaptive_engine.py", "auth_service.py", "config.py",
    "engine/thresholds.py", "engine/adaptive_difficulty.py",
    "engine/skill_engine.py", "engine/spaced_rep.py",
    "db/analytics.py", "db/chunks.py", "db/corpus.py",
    "db/skills.py", "db/profile.py",
    "tabs/tab_training.py", "tabs/tab_dashboard.py", "tabs/tab_corpus.py",
    "tools/testing/run_training_calibration_suite.py",
]

_CALIBRATION_SCRIPTS = {
    "mastery_threshold":  "tools/testing/calibrate_mastery_threshold.py",
    "mastery_boundaries": "tools/testing/calibrate_mastery_boundaries.py",
    "adaptive_difficulty":"tools/testing/calibrate_adaptive_difficulty.py",
    "review_intervals":   "tools/testing/calibrate_review_intervals.py",
}

# ── Couleurs ANSI ─────────────────────────────────────────────────────────────
_C = {
    "OK":       "\033[92m",
    "WARNING":  "\033[93m",
    "CRITICAL": "\033[91m",
    "FAILED":   "\033[1;91m",
    "SECTION":  "\033[1;36m",
    "RESET":    "\033[0m",
    "BOLD":     "\033[1m",
    "DIM":      "\033[2m",
}


def _colored(status: str, text: str) -> str:
    return f"{_C.get(status, '')}{text}{_C['RESET']}"


# ── Dataclass résultat ────────────────────────────────────────────────────────
@dataclass
class Check:
    section: str
    name: str
    status: Literal["OK", "WARNING", "CRITICAL", "FAILED"]
    message: str
    detail: str = ""
    score_deduct: float = 0.0

    def label(self) -> str:
        icons = {"OK": "✅", "WARNING": "⚠️ ", "CRITICAL": "❌", "FAILED": "💥"}
        return f"{icons.get(self.status, '?')} [{self.status:8}] {self.name}"


# ── Connexion DB (read-only) ──────────────────────────────────────────────────
def _db() -> Optional[sqlite3.Connection]:
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _q(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list:
    try:
        return conn.execute(sql, params).fetchall()
    except Exception:
        return []


def _q1(conn: sqlite3.Connection, sql: str, params: tuple = ()):
    rows = _q(conn, sql, params)
    return rows[0] if rows else None


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple = (), default=0):
    row = _q1(conn, sql, params)
    if row is None:
        return default
    val = row[0]
    return val if val is not None else default


# ── Section 1 : STRUCTURE (15 pts) ────────────────────────────────────────────
def audit_structure(verbose: bool) -> list[Check]:
    checks: list[Check] = []
    max_deduct = 15.0

    # Fichiers clés présents
    missing = [f for f in _KEY_FILES if not (_ROOT / f).exists()]
    if missing:
        checks.append(Check(
            "STRUCTURE", "Fichiers clés",
            "CRITICAL" if len(missing) > 3 else "WARNING",
            f"{len(missing)} fichier(s) manquant(s)",
            "\n  ".join(missing),
            score_deduct=min(len(missing) * 1.5, 8.0),
        ))
    else:
        checks.append(Check("STRUCTURE", "Fichiers clés", "OK",
                            f"{len(_KEY_FILES)} fichiers clés présents"))

    # py_compile modules principaux
    _compile_targets = [
        "database.py", "ai_service.py", "document_service.py",
        "adaptive_engine.py", "auth_service.py",
        "engine/thresholds.py", "engine/skill_engine.py",
        "db/analytics.py", "db/chunks.py", "db/corpus.py",
        "tabs/tab_training.py", "tabs/tab_dashboard.py", "tabs/tab_corpus.py",
        "app.py",
    ]
    failed_compile = []
    for rel in _compile_targets:
        path = _ROOT / rel
        if not path.exists():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            failed_compile.append(f"{rel}: {e}")

    if failed_compile:
        checks.append(Check(
            "STRUCTURE", "py_compile", "FAILED",
            f"{len(failed_compile)} module(s) ne compilent pas",
            "\n  ".join(failed_compile),
            score_deduct=10.0,
        ))
    else:
        checks.append(Check("STRUCTURE", "py_compile", "OK",
                            f"{len(_compile_targets)} modules compilés sans erreur"))

    # Imports critiques
    _imports_ok = []
    _imports_fail = []
    for mod in ("database", "adaptive_engine", "auth_service"):
        try:
            __import__(mod)
            _imports_ok.append(mod)
        except Exception as e:
            _imports_fail.append(f"{mod}: {e}")

    if _imports_fail:
        checks.append(Check(
            "STRUCTURE", "Imports critiques", "CRITICAL",
            f"{len(_imports_fail)} import(s) échoué(s)",
            "\n  ".join(_imports_fail),
            score_deduct=8.0,
        ))
    else:
        checks.append(Check("STRUCTURE", "Imports critiques", "OK",
                            f"{len(_imports_ok)} imports critiques OK"))

    # Thresholds lisibles
    try:
        from engine.thresholds import (
            MASTERY_FRAGILE, MASTERY_MASTERED, MASTERY_MIN_ATTEMPTS,
            ADAPTIVE_FORCE_EASY, ADAPTIVE_ALLOW_HARD, REVIEW_INTERVALS,
        )
        th_str = (
            f"FRAGILE={MASTERY_FRAGILE} MASTERED={MASTERY_MASTERED} "
            f"MIN_ATTEMPTS={MASTERY_MIN_ATTEMPTS} FORCE_EASY={ADAPTIVE_FORCE_EASY} "
            f"ALLOW_HARD={ADAPTIVE_ALLOW_HARD} INTERVALS={REVIEW_INTERVALS}"
        )
        checks.append(Check("STRUCTURE", "Engine thresholds", "OK",
                            "Tous les seuils lisibles", th_str))
    except Exception as e:
        checks.append(Check("STRUCTURE", "Engine thresholds", "FAILED",
                            f"Impossible de lire engine/thresholds.py: {e}",
                            score_deduct=5.0))

    return checks


# ── Section 2 : DATABASE (20 pts) ─────────────────────────────────────────────
def audit_database(conn: Optional[sqlite3.Connection], verbose: bool) -> list[Check]:
    checks: list[Check] = []

    if conn is None:
        checks.append(Check("DATABASE", "Fichier DB", "FAILED",
                            f"database.db introuvable : {DB_PATH}",
                            score_deduct=20.0))
        return checks

    checks.append(Check("DATABASE", "Fichier DB", "OK",
                        f"database.db présent ({DB_PATH.stat().st_size // 1024} Ko)"))

    # Tables présentes
    tables = {r[0] for r in _q(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    missing_tables = [t for t in _EXPECTED_TABLES if t not in tables]
    if missing_tables:
        checks.append(Check("DATABASE", "Tables attendues", "FAILED",
                            f"Tables manquantes : {', '.join(missing_tables)}",
                            score_deduct=3.0 * len(missing_tables)))
    else:
        checks.append(Check("DATABASE", "Tables attendues", "OK",
                            f"{len(_EXPECTED_TABLES)} tables présentes"))

    # Index principaux
    indexes = {r[0] for r in _q(conn, "SELECT name FROM sqlite_master WHERE type='index'")}
    expected_idx = ["idx_rm_timestamp", "idx_rm_user", "idx_corpus_user", "idx_corpus_doc"]
    missing_idx = [i for i in expected_idx if i not in indexes]
    if missing_idx:
        checks.append(Check("DATABASE", "Index", "WARNING",
                            f"Index manquants : {', '.join(missing_idx)}",
                            score_deduct=1.0))
    else:
        checks.append(Check("DATABASE", "Index", "OK", "Index principaux présents"))

    # Comptages
    n_users    = _scalar(conn, "SELECT COUNT(*) FROM users")
    n_docs     = _scalar(conn, "SELECT COUNT(*) FROM documents")
    n_chunks   = _scalar(conn, "SELECT COUNT(*) FROM chunks")
    n_attempts = _scalar(conn, "SELECT COUNT(*) FROM attempts")
    n_corpus   = _scalar(conn, "SELECT COUNT(*) FROM corpus") if "corpus" in tables else 0
    n_rm       = _scalar(conn, "SELECT COUNT(*) FROM runtime_metrics") if "runtime_metrics" in tables else 0

    counts_str = (
        f"users={n_users} | docs={n_docs} | chunks={n_chunks} | "
        f"attempts={n_attempts} | corpus={n_corpus} | runtime_metrics={n_rm}"
    )
    if n_docs == 0:
        checks.append(Check("DATABASE", "Comptages", "WARNING",
                            "Aucun document en base", counts_str, score_deduct=2.0))
    elif n_chunks == 0:
        checks.append(Check("DATABASE", "Comptages", "WARNING",
                            "Documents présents mais aucun chunk", counts_str, score_deduct=2.0))
    else:
        checks.append(Check("DATABASE", "Comptages", "OK", counts_str))

    # Colonnes attendues — attempts
    if "attempts" in tables:
        cols_attempts = {r[1] for r in _q(conn, "PRAGMA table_info(attempts)")}
        expected_cols = {"id", "user_id", "score", "error_type", "chunk_id", "document_id", "pedagogy_type"}
        missing_cols = expected_cols - cols_attempts
        if missing_cols:
            checks.append(Check("DATABASE", "Colonnes attempts", "WARNING",
                                f"Colonnes manquantes : {', '.join(missing_cols)}",
                                score_deduct=1.0))
        else:
            checks.append(Check("DATABASE", "Colonnes attempts", "OK",
                                "Colonnes attempts attendues présentes"))

    # Orphelins DB-level
    orphan_attempts_chunk = _scalar(conn,
        "SELECT COUNT(*) FROM attempts a WHERE a.chunk_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM chunks c WHERE c.id = a.chunk_id)"
    )
    orphan_attempts_doc = _scalar(conn,
        "SELECT COUNT(*) FROM attempts a WHERE a.document_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = a.document_id)"
    )
    orphan_chunks_doc = _scalar(conn,
        "SELECT COUNT(*) FROM chunks c WHERE NOT EXISTS "
        "(SELECT 1 FROM documents d WHERE d.id = c.document_id)"
    )

    orphan_total = orphan_attempts_chunk + orphan_attempts_doc + orphan_chunks_doc
    detail = (f"attempts→chunk orphelins: {orphan_attempts_chunk} | "
              f"attempts→doc orphelins: {orphan_attempts_doc} | "
              f"chunks→doc orphelins: {orphan_chunks_doc}")
    if orphan_total > 10:
        checks.append(Check("DATABASE", "Orphelins DB", "WARNING",
                            f"{orphan_total} lignes orphelines détectées", detail,
                            score_deduct=2.0))
    elif orphan_total > 0:
        checks.append(Check("DATABASE", "Orphelins DB", "WARNING",
                            f"{orphan_total} ligne(s) orpheline(s)", detail))
    else:
        checks.append(Check("DATABASE", "Orphelins DB", "OK",
                            "Aucun orphelin détecté"))

    return checks


# ── Section 3 : CORPUS (15 pts) ───────────────────────────────────────────────
def audit_corpus(conn: Optional[sqlite3.Connection], verbose: bool) -> list[Check]:
    checks: list[Check] = []
    if conn is None:
        return checks

    tables = {r[0] for r in _q(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    if "corpus" not in tables or "corpus_documents" not in tables:
        checks.append(Check("CORPUS", "Tables corpus", "FAILED",
                            "Tables corpus / corpus_documents manquantes",
                            score_deduct=15.0))
        return checks

    n_corpus = _scalar(conn, "SELECT COUNT(*) FROM corpus")
    if n_corpus == 0:
        checks.append(Check("CORPUS", "Corpus créés", "OK",
                            "Aucun corpus créé — comportement nominal (fallback toutes sources)"))
        return checks

    checks.append(Check("CORPUS", "Corpus créés", "OK", f"{n_corpus} corpus en base"))

    # Corpus sans documents
    empty_corpus = _scalar(conn,
        "SELECT COUNT(*) FROM corpus c WHERE NOT EXISTS "
        "(SELECT 1 FROM corpus_documents cd WHERE cd.corpus_id = c.id)"
    )
    if empty_corpus:
        rows = _q(conn,
            "SELECT c.id, c.corpus_name, c.user_id FROM corpus c WHERE NOT EXISTS "
            "(SELECT 1 FROM corpus_documents cd WHERE cd.corpus_id = c.id)"
        )
        names = ", ".join(f"'{r['corpus_name']}' (user={r['user_id']})" for r in rows)
        checks.append(Check("CORPUS", "Corpus vides", "WARNING",
                            f"{empty_corpus} corpus sans document(s)",
                            names, score_deduct=2.0))
    else:
        checks.append(Check("CORPUS", "Corpus vides", "OK",
                            "Tous les corpus ont au moins un document"))

    # corpus_documents → document inexistant
    invalid_doc_refs = _scalar(conn,
        "SELECT COUNT(*) FROM corpus_documents cd WHERE NOT EXISTS "
        "(SELECT 1 FROM documents d WHERE d.id = cd.document_id)"
    )
    if invalid_doc_refs:
        checks.append(Check("CORPUS", "Liens corpus→doc invalides", "CRITICAL",
                            f"{invalid_doc_refs} lien(s) corpus_documents pointent vers document inexistant",
                            score_deduct=5.0))
    else:
        checks.append(Check("CORPUS", "Liens corpus→doc", "OK",
                            "Tous les liens corpus→document sont valides"))

    # Corpus appartenant à user inexistant
    orphan_corpus = _scalar(conn,
        "SELECT COUNT(*) FROM corpus c WHERE NOT EXISTS "
        "(SELECT 1 FROM users u WHERE u.user_id = c.user_id)"
        " AND c.user_id != 'default'"
    )
    if orphan_corpus:
        checks.append(Check("CORPUS", "Corpus user inexistant", "WARNING",
                            f"{orphan_corpus} corpus appartenant à un user introuvable",
                            score_deduct=1.0))
    else:
        checks.append(Check("CORPUS", "Corpus propriétaires", "OK",
                            "Tous les corpus ont un propriétaire valide"))

    # Distribution taille corpus
    rows = _q(conn,
        "SELECT c.corpus_name, COUNT(cd.document_id) AS n_docs "
        "FROM corpus c LEFT JOIN corpus_documents cd ON cd.corpus_id = c.id "
        "GROUP BY c.id ORDER BY n_docs DESC"
    )
    if verbose and rows:
        detail = " | ".join(f"'{r['corpus_name']}'={r['n_docs']} docs" for r in rows)
        checks.append(Check("CORPUS", "Distribution corpus", "OK",
                            f"{len(rows)} corpus", detail))

    return checks


# ── Section 4 : LEARNING DATA / ATTEMPTS (15 pts) ─────────────────────────────
def audit_learning_data(conn: Optional[sqlite3.Connection], verbose: bool) -> list[Check]:
    checks: list[Check] = []
    if conn is None:
        return checks

    n_total = _scalar(conn, "SELECT COUNT(*) FROM attempts")
    if n_total == 0:
        checks.append(Check("LEARNING", "Attempts", "WARNING",
                            "Aucune tentative enregistrée — données d'apprentissage vides",
                            score_deduct=3.0))
        return checks

    checks.append(Check("LEARNING", "Attempts total", "OK",
                        f"{n_total} tentatives enregistrées"))

    # Attempts sans user_id valide
    no_user = _scalar(conn,
        "SELECT COUNT(*) FROM attempts WHERE user_id IS NULL OR TRIM(user_id) = ''"
    )
    if no_user:
        checks.append(Check("LEARNING", "Attempts sans user_id", "CRITICAL",
                            f"{no_user}/{n_total} tentatives sans user_id",
                            score_deduct=3.0))
    else:
        checks.append(Check("LEARNING", "Attempts user_id", "OK",
                            "Toutes les tentatives ont un user_id"))

    # Attempts sans score
    no_score = _scalar(conn, "SELECT COUNT(*) FROM attempts WHERE score IS NULL")
    if no_score > n_total * 0.1:
        checks.append(Check("LEARNING", "Attempts sans score", "WARNING",
                            f"{no_score}/{n_total} tentatives sans score ({round(no_score/n_total*100)}%)",
                            score_deduct=2.0))
    elif no_score > 0:
        checks.append(Check("LEARNING", "Attempts sans score", "WARNING",
                            f"{no_score} tentative(s) sans score"))
    else:
        checks.append(Check("LEARNING", "Attempts scores", "OK",
                            "Tous les scores présents"))

    # Scores hors [0,1]
    out_of_range = _scalar(conn,
        "SELECT COUNT(*) FROM attempts WHERE score IS NOT NULL AND (score < 0 OR score > 1)"
    )
    if out_of_range:
        checks.append(Check("LEARNING", "Scores hors [0,1]", "CRITICAL",
                            f"{out_of_range} score(s) hors intervalle valide",
                            score_deduct=4.0))
    else:
        checks.append(Check("LEARNING", "Plage scores", "OK",
                            "Tous les scores dans [0,1]"))

    # chunk_id inexistant
    bad_chunks = _scalar(conn,
        "SELECT COUNT(*) FROM attempts WHERE chunk_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM chunks c WHERE c.id = attempts.chunk_id)"
    )
    if bad_chunks:
        checks.append(Check("LEARNING", "chunk_id invalides", "CRITICAL",
                            f"{bad_chunks} attempts avec chunk_id inexistant",
                            score_deduct=3.0))
    else:
        checks.append(Check("LEARNING", "chunk_id cohérents", "OK",
                            "Tous les chunk_id référencent des chunks existants"))

    # error_type inconnus
    known = "','".join(_KNOWN_ERROR_TYPES)
    unknown_errors = _scalar(conn,
        f"SELECT COUNT(*) FROM attempts WHERE error_type IS NOT NULL "
        f"AND error_type NOT IN ('{known}')"
    )
    if unknown_errors:
        rows = _q(conn,
            f"SELECT DISTINCT error_type FROM attempts WHERE error_type IS NOT NULL "
            f"AND error_type NOT IN ('{known}') LIMIT 10"
        )
        detail = ", ".join(r[0] for r in rows)
        checks.append(Check("LEARNING", "error_type inconnus", "WARNING",
                            f"{unknown_errors} tentative(s) avec error_type inconnu",
                            f"Types inconnus : {detail}", score_deduct=1.0))
    else:
        checks.append(Check("LEARNING", "error_type", "OK",
                            "Tous les error_types reconnus"))

    # question_type (pedagogy_type) inconnus
    known_qt = "','".join(_KNOWN_QUESTION_TYPES)
    unknown_qt = _scalar(conn,
        f"SELECT COUNT(*) FROM attempts WHERE pedagogy_type IS NOT NULL "
        f"AND pedagogy_type NOT IN ('{known_qt}')"
    )
    if unknown_qt:
        rows = _q(conn,
            f"SELECT DISTINCT pedagogy_type FROM attempts WHERE pedagogy_type IS NOT NULL "
            f"AND pedagogy_type NOT IN ('{known_qt}') LIMIT 10"
        )
        detail = ", ".join(r[0] for r in rows)
        checks.append(Check("LEARNING", "question_type inconnus", "WARNING",
                            f"{unknown_qt} tentative(s) avec pedagogy_type inconnu",
                            f"Types : {detail}", score_deduct=1.0))
    else:
        checks.append(Check("LEARNING", "question_type", "OK",
                            "Tous les pedagogy_types reconnus"))

    # Score moyen global
    avg = _scalar(conn, "SELECT ROUND(AVG(score),3) FROM attempts WHERE score IS NOT NULL")
    if avg is not None:
        status = "OK" if 0.3 <= float(avg) <= 0.95 else "WARNING"
        checks.append(Check("LEARNING", "Score moyen global", status,
                            f"Score moyen : {avg}"))

    return checks


# ── Section 5 : CHUNKS / DOCUMENTS ────────────────────────────────────────────
def audit_chunks(conn: Optional[sqlite3.Connection], verbose: bool) -> list[Check]:
    checks: list[Check] = []
    if conn is None:
        return checks

    n_docs   = _scalar(conn, "SELECT COUNT(*) FROM documents")
    n_chunks = _scalar(conn, "SELECT COUNT(*) FROM chunks")

    if n_docs == 0:
        checks.append(Check("CHUNKS", "Documents", "WARNING",
                            "Aucun document en base — impossible d'auditer les chunks"))
        return checks

    # Documents sans chunks
    docs_no_chunks = _scalar(conn,
        "SELECT COUNT(*) FROM documents d WHERE NOT EXISTS "
        "(SELECT 1 FROM chunks c WHERE c.document_id = d.id)"
    )
    if docs_no_chunks:
        rows = _q(conn,
            "SELECT title FROM documents d WHERE NOT EXISTS "
            "(SELECT 1 FROM chunks c WHERE c.document_id = d.id) LIMIT 5"
        )
        detail = ", ".join(f"'{r[0]}'" for r in rows)
        checks.append(Check("CHUNKS", "Documents sans chunks", "WARNING",
                            f"{docs_no_chunks}/{n_docs} document(s) sans chunks",
                            detail, score_deduct=2.0))
    else:
        checks.append(Check("CHUNKS", "Couverture chunks", "OK",
                            f"{n_docs} docs, {n_chunks} chunks"))

    # Chunks trop courts (<50 chars)
    too_short = _scalar(conn,
        "SELECT COUNT(*) FROM chunks WHERE LENGTH(chunk_text) < 50"
    )
    if too_short > 0:
        pct = round(too_short / max(n_chunks, 1) * 100)
        status = "CRITICAL" if pct > 20 else "WARNING"
        checks.append(Check("CHUNKS", "Chunks trop courts", status,
                            f"{too_short} chunk(s) < 50 chars ({pct}%)",
                            score_deduct=2.0 if pct > 20 else 0.0))
    else:
        checks.append(Check("CHUNKS", "Longueur minimale", "OK",
                            "Aucun chunk trop court"))

    # Chunks trop longs (>10000 chars)
    too_long = _scalar(conn,
        "SELECT COUNT(*) FROM chunks WHERE LENGTH(chunk_text) > 10000"
    )
    if too_long > 0:
        checks.append(Check("CHUNKS", "Chunks trop longs", "WARNING",
                            f"{too_long} chunk(s) > 10 000 chars"))
    else:
        checks.append(Check("CHUNKS", "Longueur maximale", "OK",
                            "Aucun chunk excessivement long"))

    # Chunks sans skill
    tables = {r[0] for r in _q(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    if "chunk_skills" in tables:
        chunks_no_skill = _scalar(conn,
            "SELECT COUNT(*) FROM chunks c WHERE NOT EXISTS "
            "(SELECT 1 FROM chunk_skills cs WHERE cs.chunk_id = c.id AND cs.is_active = 1)"
        )
        if chunks_no_skill > 0:
            pct = round(chunks_no_skill / max(n_chunks, 1) * 100)
            status = "WARNING" if pct < 50 else "CRITICAL"
            checks.append(Check("CHUNKS", "Chunks sans skill", status,
                                f"{chunks_no_skill}/{n_chunks} chunks sans skill ({pct}%)"))
        else:
            checks.append(Check("CHUNKS", "Skills par chunk", "OK",
                                "Tous les chunks ont au moins un skill"))

    # Documents avec taux d'échec élevé
    bad_docs = _q(conn,
        "SELECT d.title, ROUND(AVG(a.score),2) AS avg_score, COUNT(*) AS n "
        "FROM attempts a JOIN chunks c ON a.chunk_id = c.id "
        "JOIN documents d ON c.document_id = d.id "
        "WHERE a.score IS NOT NULL "
        "GROUP BY d.id HAVING avg_score < 0.4 AND n >= 5 "
        "ORDER BY avg_score ASC LIMIT 5"
    )
    if bad_docs:
        detail = " | ".join(f"'{r['title']}' avg={r['avg_score']}({r['n']} attempts)" for r in bad_docs)
        checks.append(Check("CHUNKS", "Documents en difficulté", "WARNING",
                            f"{len(bad_docs)} document(s) avec score moyen < 40%",
                            detail))
    elif n_chunks > 0:
        checks.append(Check("CHUNKS", "Taux réussite docs", "OK",
                            "Aucun document en difficulté critique"))

    return checks


# ── Section 6 : SKILLS ENGINE (10 pts) ────────────────────────────────────────
def audit_skills(conn: Optional[sqlite3.Connection], verbose: bool) -> list[Check]:
    checks: list[Check] = []
    if conn is None:
        return checks

    tables = {r[0] for r in _q(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    if "skills" not in tables:
        checks.append(Check("SKILLS", "Table skills", "FAILED",
                            "Table skills absente", score_deduct=10.0))
        return checks

    # 10 skills attendus
    slugs_present = {r[0] for r in _q(conn, "SELECT slug FROM skills WHERE is_active = 1")}
    missing_skills = [s for s in _EXPECTED_SKILLS if s not in slugs_present]
    if missing_skills:
        checks.append(Check("SKILLS", "Skills V1.0", "CRITICAL",
                            f"{len(missing_skills)} skill(s) manquant(s)",
                            ", ".join(missing_skills), score_deduct=3.0))
    else:
        checks.append(Check("SKILLS", "Skills V1.0", "OK",
                            f"10 skills opérationnels"))

    # Thresholds affichés
    try:
        from engine.thresholds import (
            MASTERY_FRAGILE, MASTERY_MASTERED, MASTERY_MIN_ATTEMPTS,
            ADAPTIVE_FORCE_EASY, ADAPTIVE_ALLOW_HARD, REVIEW_INTERVALS,
        )
        detail = (
            f"FRAGILE={MASTERY_FRAGILE} | MASTERED={MASTERY_MASTERED} | "
            f"MIN_ATTEMPTS={MASTERY_MIN_ATTEMPTS}\n"
            f"  FORCE_EASY={ADAPTIVE_FORCE_EASY} | ALLOW_HARD={ADAPTIVE_ALLOW_HARD}\n"
            f"  REVIEW_INTERVALS={REVIEW_INTERVALS}"
        )
        checks.append(Check("SKILLS", "Thresholds moteur", "OK",
                            "6 seuils validés Phase 18C", detail))
    except Exception as e:
        checks.append(Check("SKILLS", "Thresholds moteur", "FAILED",
                            f"Impossible de lire les seuils : {e}",
                            score_deduct=3.0))

    if "chunk_skills" in tables:
        # chunk_skills orphelins
        orphan_cs = _scalar(conn,
            "SELECT COUNT(*) FROM chunk_skills WHERE NOT EXISTS "
            "(SELECT 1 FROM chunks c WHERE c.id = chunk_skills.chunk_id)"
        )
        if orphan_cs:
            checks.append(Check("SKILLS", "chunk_skills orphelins", "WARNING",
                                f"{orphan_cs} entrées chunk_skills sans chunk valide",
                                score_deduct=1.0))
        else:
            checks.append(Check("SKILLS", "chunk_skills cohérents", "OK",
                                "Tous les chunk_skills référencent un chunk valide"))

    if "user_skill_mastery" in tables:
        n_usm = _scalar(conn, "SELECT COUNT(*) FROM user_skill_mastery")
        if n_usm > 0:
            # mastery_score hors [0,1]
            bad_score = _scalar(conn,
                "SELECT COUNT(*) FROM user_skill_mastery "
                "WHERE mastery_score < 0 OR mastery_score > 1"
            )
            if bad_score:
                checks.append(Check("SKILLS", "mastery_score hors [0,1]", "CRITICAL",
                                    f"{bad_score} mastery_score hors intervalle",
                                    score_deduct=2.0))
            else:
                checks.append(Check("SKILLS", "mastery_score valide", "OK",
                                    f"{n_usm} user_skill_mastery dans [0,1]"))

            # orphelins skill_id
            orphan_usm_skill = _scalar(conn,
                "SELECT COUNT(*) FROM user_skill_mastery WHERE NOT EXISTS "
                "(SELECT 1 FROM skills s WHERE s.id = user_skill_mastery.skill_id)"
            )
            if orphan_usm_skill:
                checks.append(Check("SKILLS", "user_skill_mastery orphelins", "WARNING",
                                    f"{orphan_usm_skill} entrées sans skill valide",
                                    score_deduct=1.0))

    return checks


# ── Section 7 : RUNTIME METRICS (10 pts) ──────────────────────────────────────
def audit_runtime(conn: Optional[sqlite3.Connection], verbose: bool) -> list[Check]:
    checks: list[Check] = []
    if conn is None:
        return checks

    tables = {r[0] for r in _q(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    if "runtime_metrics" not in tables:
        checks.append(Check("RUNTIME", "Table runtime_metrics", "WARNING",
                            "Table runtime_metrics absente", score_deduct=5.0))
        return checks

    n_rm = _scalar(conn, "SELECT COUNT(*) FROM runtime_metrics")
    if n_rm == 0:
        checks.append(Check("RUNTIME", "Métriques", "OK",
                            "Aucune métrique runtime — application pas encore utilisée en mode API"))
        return checks

    checks.append(Check("RUNTIME", "Métriques présentes", "OK",
                        f"{n_rm} métriques runtime enregistrées"))

    # Métriques sans user
    no_user = _scalar(conn,
        "SELECT COUNT(*) FROM runtime_metrics "
        "WHERE user_id IS NULL OR TRIM(user_id) = ''"
    )
    if no_user:
        checks.append(Check("RUNTIME", "Métriques sans user", "WARNING",
                            f"{no_user} métriques sans user_id",
                            score_deduct=1.0))

    # Latence anormale (>30s ou négative)
    bad_latency = _scalar(conn,
        "SELECT COUNT(*) FROM runtime_metrics "
        "WHERE latency_ms IS NOT NULL AND (latency_ms < 0 OR latency_ms > 30000)"
    )
    if bad_latency:
        checks.append(Check("RUNTIME", "Latences anormales", "WARNING",
                            f"{bad_latency} métriques avec latence hors plage (<0 ou >30s)",
                            score_deduct=1.0))
    else:
        checks.append(Check("RUNTIME", "Latences", "OK",
                            "Latences dans la plage normale"))

    # Coûts négatifs
    bad_cost = _scalar(conn,
        "SELECT COUNT(*) FROM runtime_metrics "
        "WHERE estimated_cost IS NOT NULL AND estimated_cost < 0"
    )
    if bad_cost:
        checks.append(Check("RUNTIME", "Coûts négatifs", "WARNING",
                            f"{bad_cost} métrique(s) avec coût estimé négatif",
                            score_deduct=1.0))

    # Fallback rate global
    n_fallback = _scalar(conn,
        "SELECT COUNT(*) FROM runtime_metrics WHERE fallback_used = 1"
    )
    fb_rate = round(n_fallback / max(n_rm, 1) * 100, 1)
    if fb_rate > 30:
        checks.append(Check("RUNTIME", "Fallback rate", "WARNING",
                            f"Taux de fallback élevé : {fb_rate}% ({n_fallback}/{n_rm})",
                            score_deduct=2.0))
    else:
        checks.append(Check("RUNTIME", "Fallback rate", "OK",
                            f"Taux de fallback : {fb_rate}%"))

    # Taux d'erreur global
    n_errors = _scalar(conn,
        "SELECT COUNT(*) FROM runtime_metrics WHERE success = 0"
    )
    err_rate = round(n_errors / max(n_rm, 1) * 100, 1)
    if err_rate > 20:
        # Top endpoints en erreur
        top_err = _q(conn,
            "SELECT endpoint, COUNT(*) AS n FROM runtime_metrics "
            "WHERE success = 0 GROUP BY endpoint ORDER BY n DESC LIMIT 5"
        )
        detail = " | ".join(f"{r['endpoint']}:{r['n']}" for r in top_err if r['endpoint'])
        checks.append(Check("RUNTIME", "Taux erreur", "WARNING",
                            f"Taux d'erreur : {err_rate}% ({n_errors}/{n_rm})",
                            detail, score_deduct=2.0))
    else:
        checks.append(Check("RUNTIME", "Taux erreur", "OK",
                            f"Taux d'erreur API : {err_rate}%"))

    return checks


# ── Section 8 : CALIBRATION ───────────────────────────────────────────────────
def audit_calibration(run_calibration: bool, verbose: bool) -> list[Check]:
    checks: list[Check] = []

    # Vérifier présence des scripts
    all_present = True
    for name, rel_path in _CALIBRATION_SCRIPTS.items():
        p = _ROOT / rel_path
        if not p.exists():
            checks.append(Check("CALIBRATION", f"Script {name}", "WARNING",
                                f"Script manquant : {rel_path}"))
            all_present = False

    if all_present:
        checks.append(Check("CALIBRATION", "Scripts présents", "OK",
                            f"{len(_CALIBRATION_SCRIPTS)} scripts de calibration présents"))

    # Runner présent
    runner = _ROOT / "tools/testing/run_training_calibration_suite.py"
    if runner.exists():
        checks.append(Check("CALIBRATION", "Suite runner", "OK",
                            "run_training_calibration_suite.py présent"))
    else:
        checks.append(Check("CALIBRATION", "Suite runner", "WARNING",
                            "run_training_calibration_suite.py introuvable"))

    if not run_calibration:
        checks.append(Check("CALIBRATION", "Exécution", "OK",
                            "Calibration non exécutée (passer --check-calibration pour lancer)"))
        return checks

    # Lancer le runner en mode --quick
    try:
        result = subprocess.run(
            [sys.executable, str(runner), "--quick", "--no-regression"],
            capture_output=True, text=True, timeout=60,
            cwd=str(_ROOT),
        )
        if result.returncode == 0:
            checks.append(Check("CALIBRATION", "Suite --quick", "OK",
                                "GO SAFE — toutes calibrations PASS",
                                result.stdout[-500:] if verbose else ""))
        else:
            checks.append(Check("CALIBRATION", "Suite --quick", "WARNING",
                                "Verdict WARNING ou FAILED — voir run_training_calibration_suite.py",
                                (result.stdout + result.stderr)[-500:]))
    except subprocess.TimeoutExpired:
        checks.append(Check("CALIBRATION", "Suite --quick", "WARNING",
                            "Timeout (>60s) sur --quick"))
    except Exception as e:
        checks.append(Check("CALIBRATION", "Suite --quick", "WARNING",
                            f"Erreur d'exécution : {e}"))

    return checks


# ── Section 9 : SECURITY / DEPLOY (10 pts) ────────────────────────────────────
def audit_security(verbose: bool) -> list[Check]:
    checks: list[Check] = []
    total_deduct = 0.0

    # .env
    env_path = _ROOT / ".env"
    if env_path.exists():
        checks.append(Check("SECURITY", ".env fichier", "OK", ".env présent"))
    else:
        checks.append(Check("SECURITY", ".env fichier", "WARNING",
                            ".env absent — vérifier .env.example",
                            score_deduct=2.0))

    # Clés d'environnement (sans afficher les valeurs)
    for key, label in [("OPENAI_API_KEY", "OpenAI API Key"), ("SENTRY_DSN", "Sentry DSN")]:
        val = os.getenv(key, "")
        if val and val.strip():
            checks.append(Check("SECURITY", label, "OK", f"{key} définie"))
        else:
            # Tenter lecture depuis .env
            found = False
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.strip().startswith(f"{key}=") and "=" in line:
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            found = True
                            break
            if found:
                checks.append(Check("SECURITY", label, "OK",
                                    f"{key} définie dans .env"))
            else:
                deduct = 3.0 if key == "OPENAI_API_KEY" else 1.0
                checks.append(Check("SECURITY", label, "WARNING",
                                    f"{key} non définie — mode fallback actif",
                                    score_deduct=deduct))

    # database.db
    if DB_PATH.exists():
        size_kb = DB_PATH.stat().st_size // 1024
        size_mb = size_kb / 1024
        status = "OK"
        detail = f"{size_kb} Ko"
        if size_mb > 500:
            status = "WARNING"
            detail += " — DB volumineuse, envisager backup"
        checks.append(Check("SECURITY", "database.db taille", status,
                            f"database.db : {detail}"))
    else:
        checks.append(Check("SECURITY", "database.db", "WARNING",
                            "database.db absent", score_deduct=2.0))

    # Backup récent
    backup_dir = _ROOT / "backups"
    if backup_dir.exists():
        backups = sorted(backup_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            latest = backups[0]
            age_days = (datetime.now().timestamp() - latest.stat().st_mtime) / 86400
            if age_days > 7:
                checks.append(Check("SECURITY", "Backup récent", "WARNING",
                                    f"Dernier backup : {round(age_days)} jours — recommandé < 7j"))
            else:
                checks.append(Check("SECURITY", "Backup récent", "OK",
                                    f"Backup récent : {latest.name} ({round(age_days, 1)}j)"))
        else:
            checks.append(Check("SECURITY", "Backup", "WARNING",
                                "Répertoire backups vide"))
    else:
        checks.append(Check("SECURITY", "Backup", "WARNING",
                            "Répertoire backups absent"))

    # Dockerfile / requirements.txt / docker-compose.yml
    for fname, label in [
        ("Dockerfile", "Dockerfile"),
        ("docker-compose.yml", "docker-compose.yml"),
        ("requirements.txt", "requirements.txt"),
    ]:
        if (_ROOT / fname).exists():
            checks.append(Check("SECURITY", label, "OK", f"{fname} présent"))
        else:
            checks.append(Check("SECURITY", label, "WARNING",
                                f"{fname} absent", score_deduct=1.0))

    return checks


# ── Section 10 : TESTS (5 pts) ────────────────────────────────────────────────
def audit_tests(run_tests: bool, verbose: bool) -> list[Check]:
    checks: list[Check] = []

    # Présence des fichiers
    test_files = {
        "test_regression.py": _ROOT / "test_regression.py",
        "test_integration.py": _ROOT / "test_integration.py",
        "test_auth_service.py": _ROOT / "test_auth_service.py",
    }
    for name, path in test_files.items():
        if path.exists():
            checks.append(Check("TESTS", f"Fichier {name}", "OK", f"{name} présent"))
        else:
            checks.append(Check("TESTS", f"Fichier {name}", "WARNING",
                                f"{name} introuvable"))

    if not run_tests:
        checks.append(Check("TESTS", "Exécution", "OK",
                            "Tests non exécutés (passer --run-tests pour lancer)"))
        return checks

    # Exécuter test_regression.py
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test_regression.py", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=120,
            cwd=str(_ROOT),
        )
        last = result.stdout.strip().splitlines()
        summary = last[-1] if last else "(pas de sortie)"
        if result.returncode == 0:
            checks.append(Check("TESTS", "test_regression.py", "OK", summary))
        else:
            checks.append(Check("TESTS", "test_regression.py", "FAILED",
                                f"Tests échoués : {summary}",
                                result.stdout[-1000:] if verbose else "",
                                score_deduct=5.0))
    except subprocess.TimeoutExpired:
        checks.append(Check("TESTS", "test_regression.py", "WARNING",
                            "Timeout (>120s)"))
    except Exception as e:
        checks.append(Check("TESTS", "test_regression.py", "FAILED",
                            f"Erreur : {e}", score_deduct=5.0))

    # test_integration.py si présent
    int_path = _ROOT / "test_integration.py"
    if int_path.exists():
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "test_integration.py", "--tb=short", "-q"],
                capture_output=True, text=True, timeout=60,
                cwd=str(_ROOT),
            )
            last = result.stdout.strip().splitlines()
            summary = last[-1] if last else "(pas de sortie)"
            status = "OK" if result.returncode == 0 else "WARNING"
            checks.append(Check("TESTS", "test_integration.py", status, summary))
        except Exception as e:
            checks.append(Check("TESTS", "test_integration.py", "WARNING", str(e)))

    return checks


# ── Calcul score ──────────────────────────────────────────────────────────────
_SECTION_MAX = {
    "STRUCTURE":   15.0,
    "DATABASE":    20.0,
    "CORPUS":      15.0,
    "LEARNING":    15.0,
    "CHUNKS":       0.0,  # audit bonus — inclus dans LEARNING data visuellement
    "SKILLS":      10.0,
    "RUNTIME":     10.0,
    "CALIBRATION":  0.0,
    "SECURITY":    10.0,
    "TESTS":        5.0,
}


def compute_score(checks: list[Check]) -> tuple[float, dict[str, float]]:
    section_deduct: dict[str, float] = {}
    for c in checks:
        section_deduct[c.section] = section_deduct.get(c.section, 0.0) + c.score_deduct

    section_scores: dict[str, float] = {}
    for sec, max_pts in _SECTION_MAX.items():
        deduct = min(section_deduct.get(sec, 0.0), max_pts)
        section_scores[sec] = max(0.0, max_pts - deduct)

    total = sum(section_scores.values())
    return round(total, 1), section_scores


# ── Affichage terminal ────────────────────────────────────────────────────────
def print_section(name: str) -> None:
    print(f"\n{_C['SECTION']}{'━'*60}{_C['RESET']}")
    print(f"{_C['SECTION']}{_C['BOLD']}  {name}{_C['RESET']}")
    print(f"{_C['SECTION']}{'━'*60}{_C['RESET']}")


def print_check(c: Check, verbose: bool) -> None:
    color = _C.get(c.status, "")
    icon = {"OK": "✅", "WARNING": "⚠️ ", "CRITICAL": "❌", "FAILED": "💥"}.get(c.status, "?")
    status_pad = f"[{c.status}]".ljust(10)
    print(f"  {color}{icon} {status_pad}{_C['RESET']} {c.name}: {_C['DIM']}{c.message}{_C['RESET']}")
    if verbose and c.detail:
        for line in c.detail.splitlines():
            print(f"             {_C['DIM']}{line}{_C['RESET']}")


def print_final_verdict(verdict: str, score: float, section_scores: dict) -> None:
    colors = {"GO SAFE": "\033[1;92m", "WARNING": "\033[1;93m", "FAILED": "\033[1;91m"}
    color = colors.get(verdict, "")
    print(f"\n{'═'*60}")
    print(f"{color}  VERDICT FINAL : {verdict}  |  Score santé : {score}/100{_C['RESET']}")
    print(f"{'═'*60}")
    print(f"\n  {_C['BOLD']}Scores par section :{_C['RESET']}")
    for sec, max_pts in _SECTION_MAX.items():
        if max_pts == 0:
            continue
        pts = section_scores.get(sec, max_pts)
        bar = "█" * int(pts / max_pts * 10) + "░" * (10 - int(pts / max_pts * 10))
        pct = round(pts / max_pts * 100)
        col = "\033[92m" if pct >= 80 else ("\033[93m" if pct >= 50 else "\033[91m")
        print(f"  {sec:12} {col}{bar}{_C['RESET']} {pts:.0f}/{max_pts:.0f} pts ({pct}%)")
    print()


# ── Rapport Markdown ──────────────────────────────────────────────────────────
def generate_report(
    checks: list[Check],
    verdict: str,
    score: float,
    section_scores: dict,
    output_path: Path,
) -> None:
    now = datetime.now()
    criticals = [c for c in checks if c.status == "CRITICAL"]
    warnings   = [c for c in checks if c.status == "WARNING"]
    failed     = [c for c in checks if c.status == "FAILED"]

    lines = [
        f"# Global System Audit — ADDISCO OPS",
        f"",
        f"> Généré le {now.strftime('%d/%m/%Y à %H:%M:%S')}",
        f"",
        f"## 1. Résumé exécutif",
        f"",
        f"| Champ | Valeur |",
        f"| --- | --- |",
        f"| Date | {now.strftime('%d/%m/%Y %H:%M')} |",
        f"| **Verdict** | **{verdict}** |",
        f"| **Score santé** | **{score}/100** |",
        f"| Checks exécutés | {len(checks)} |",
        f"| FAILED | {len(failed)} |",
        f"| CRITICAL | {len(criticals)} |",
        f"| WARNING | {len(warnings)} |",
        f"| OK | {len([c for c in checks if c.status == 'OK'])} |",
        f"",
        f"## 2. Score par section",
        f"",
        f"| Section | Score | Max | % |",
        f"| --- | --- | --- | --- |",
    ]
    for sec, max_pts in _SECTION_MAX.items():
        if max_pts == 0:
            continue
        pts = section_scores.get(sec, max_pts)
        pct = round(pts / max_pts * 100)
        emoji = "✅" if pct >= 80 else ("⚠️" if pct >= 50 else "❌")
        lines.append(f"| {emoji} {sec} | {pts:.0f} | {max_pts:.0f} | {pct}% |")

    # Erreurs critiques
    if failed or criticals:
        lines += ["", "## 3. Problèmes critiques", ""]
        for c in (failed + criticals):
            lines.append(f"### ❌ [{c.section}] {c.name}")
            lines.append(f"**Statut :** {c.status}")
            lines.append(f"**Message :** {c.message}")
            if c.detail:
                lines.append(f"```\n{c.detail}\n```")
            lines.append("")
    else:
        lines += ["", "## 3. Problèmes critiques", "", "> Aucun problème critique détecté.", ""]

    # Warnings
    if warnings:
        lines += ["## 4. Avertissements", ""]
        for c in warnings:
            detail_str = f" — `{c.detail}`" if c.detail else ""
            lines.append(f"- ⚠️ **[{c.section}] {c.name}** : {c.message}{detail_str}")
        lines.append("")
    else:
        lines += ["## 4. Avertissements", "", "> Aucun avertissement.", ""]

    # Recommandations
    lines += ["## 5. Recommandations prioritaires", ""]
    recs = []
    if failed:
        recs.append("🔴 **BLOQUANT** — Corriger les erreurs FAILED avant tout déploiement")
    if criticals:
        recs.append("🔴 **CRITIQUE** — Résoudre les checks CRITICAL avant tests humains")
    if any(c.section == "CORPUS" and c.status in ("WARNING", "CRITICAL") for c in checks):
        recs.append("🟡 Vérifier la cohérence des corpus (liens corpus→documents)")
    if any(c.section == "SECURITY" and c.status == "WARNING" for c in checks):
        recs.append("🟡 Configurer les variables d'environnement (.env) avant déploiement")
    if any(c.name == "Chunks sans skill" for c in checks if c.status != "OK"):
        recs.append("🟡 Lancer `classify_and_save_document_skills` sur les nouveaux documents")
    if not recs:
        recs.append("✅ Système sain — prêt pour tests humains et déploiement Railway")

    for r in recs:
        lines.append(f"- {r}")

    # Commandes utiles
    lines += [
        "",
        "## 6. Commandes utiles",
        "",
        "```bash",
        "# Lancer l'audit avec tests",
        "python tools/qa/global_system_auditor.py --run-tests --verbose",
        "",
        "# Calibration complète",
        "python tools/testing/run_training_calibration_suite.py --quick",
        "",
        "# Tests régression seuls",
        "python -m pytest test_regression.py -q",
        "",
        "# Démarrer l'application",
        "python -m streamlit run app.py",
        "```",
        "",
        "---",
        f"*Rapport généré par `global_system_auditor.py` — ADDISCO OPS*",
    ]

    REPORTS_DIR.mkdir(exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


# ── Verdict global ────────────────────────────────────────────────────────────
def compute_verdict(checks: list[Check], fail_on_warning: bool) -> str:
    has_failed   = any(c.status == "FAILED"   for c in checks)
    has_critical = any(c.status == "CRITICAL" for c in checks)
    has_warning  = any(c.status == "WARNING"  for c in checks)

    if has_failed or has_critical:
        return "FAILED"
    if has_warning:
        return "WARNING" if not fail_on_warning else "FAILED"
    return "GO SAFE"


# ── Sortie JSON ───────────────────────────────────────────────────────────────
def to_json(checks: list[Check], verdict: str, score: float, section_scores: dict) -> str:
    return json.dumps({
        "verdict": verdict,
        "score": score,
        "section_scores": section_scores,
        "checks": [
            {
                "section": c.section,
                "name": c.name,
                "status": c.status,
                "message": c.message,
                "detail": c.detail,
            }
            for c in checks
        ],
    }, ensure_ascii=False, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="ADDISCO OPS — Global System Auditor")
    parser.add_argument("--run-tests",         action="store_true", help="Exécuter la suite de tests")
    parser.add_argument("--verbose",           action="store_true", help="Afficher les détails")
    parser.add_argument("--json",              action="store_true", help="Sortie JSON")
    parser.add_argument("--output",            type=str,            help="Chemin rapport markdown")
    parser.add_argument("--fail-on-warning",   action="store_true", help="Verdict FAILED si WARNING")
    parser.add_argument("--check-corpus",      action="store_true", help="Audit corpus (activé par défaut)")
    parser.add_argument("--check-runtime",     action="store_true", help="Audit runtime (activé par défaut)")
    parser.add_argument("--check-calibration", action="store_true", help="Exécuter les scripts de calibration")
    args = parser.parse_args()

    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    if args.output:
        report_path = Path(args.output)
    else:
        REPORTS_DIR.mkdir(exist_ok=True)
        report_path = REPORTS_DIR / f"global_audit_{now_str}.md"

    all_checks: list[Check] = []

    if not args.json:
        print(f"\n{_C['BOLD']}{'═'*60}{_C['RESET']}")
        print(f"{_C['BOLD']}  ADDISCO OPS — Global System Auditor{_C['RESET']}")
        print(f"{_C['DIM']}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Read-only{_C['RESET']}")
        print(f"{_C['BOLD']}{'═'*60}{_C['RESET']}")

    # ── Connexion DB ──────────────────────────────────────────────────────────
    conn = _db()

    # ── Exécution des sections ────────────────────────────────────────────────
    sections = [
        ("STRUCTURE",   lambda: audit_structure(args.verbose)),
        ("DATABASE",    lambda: audit_database(conn, args.verbose)),
        ("CORPUS",      lambda: audit_corpus(conn, args.verbose)),
        ("LEARNING DATA", lambda: audit_learning_data(conn, args.verbose)),
        ("CHUNKS",      lambda: audit_chunks(conn, args.verbose)),
        ("SKILLS",      lambda: audit_skills(conn, args.verbose)),
        ("RUNTIME",     lambda: audit_runtime(conn, args.verbose)),
        ("CALIBRATION", lambda: audit_calibration(args.check_calibration, args.verbose)),
        ("SECURITY",    lambda: audit_security(args.verbose)),
        ("TESTS",       lambda: audit_tests(args.run_tests, args.verbose)),
    ]

    for section_name, fn in sections:
        if not args.json:
            print_section(section_name)
        try:
            results = fn()
        except Exception as e:
            results = [Check(section_name.upper().split()[0], "Audit section",
                             "FAILED", f"Erreur inattendue : {e}", score_deduct=5.0)]
        all_checks.extend(results)
        if not args.json:
            for c in results:
                print_check(c, args.verbose)

    if conn:
        conn.close()

    # ── Score et verdict ──────────────────────────────────────────────────────
    score, section_scores = compute_score(all_checks)
    verdict = compute_verdict(all_checks, args.fail_on_warning)

    if args.json:
        print(to_json(all_checks, verdict, score, section_scores))
    else:
        print_final_verdict(verdict, score, section_scores)

    # ── Rapport markdown ──────────────────────────────────────────────────────
    generate_report(all_checks, verdict, score, section_scores, report_path)
    if not args.json:
        print(f"  📄 Rapport : {report_path}")
        print()

    # Code retour : 0=GO SAFE, 1=WARNING, 2=FAILED
    return_codes = {"GO SAFE": 0, "WARNING": 1, "FAILED": 2}
    return return_codes.get(verdict, 2)


if __name__ == "__main__":
    sys.exit(main())
