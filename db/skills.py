"""
Skills Engine V1.0 — CRUD skills, chunk_skills, user_skill_mastery.
Utilise database.DB_PATH via import tardif (pattern identique aux autres modules db/).
"""
import logging
import sqlite3
from collections import defaultdict
from typing import Optional

import database as _db

logger = logging.getLogger(__name__)

# Slugs immuables après premier déploiement.
_SKILLS_SEED: list[tuple[str, str, str]] = [
    (
        "memorisation_faits",
        "Mémorisation de faits",
        "Retenir des informations précises : chiffres, dates, définitions, seuils",
    ),
    (
        "comprehension_procedure",
        "Compréhension de procédures",
        "Comprendre l'ordre, la logique et les conditions d'un processus",
    ),
    (
        "identification_concepts",
        "Identification de concepts",
        "Reconnaître, nommer et distinguer des notions clés dans un domaine",
    ),
    (
        "application_regles",
        "Application de règles",
        "Appliquer une règle, norme ou réglementation à une situation concrète",
    ),
    (
        "analyse_causale",
        "Analyse causale",
        "Relier causes et conséquences, comprendre pourquoi une situation se produit",
    ),
    (
        "resolution_problemes",
        "Résolution de problèmes",
        "Mobiliser plusieurs savoirs pour traiter un cas pratique",
    ),
    (
        "prise_decision",
        "Prise de décision",
        "Choisir l'action correcte parmi plusieurs options dans un contexte défini",
    ),
    (
        "evaluation_critique",
        "Évaluation critique",
        "Distinguer vrai/faux, détecter une erreur, valider une affirmation",
    ),
    (
        "synthese_reformulation",
        "Synthèse et reformulation",
        "Restituer une information complexe dans ses propres termes",
    ),
    (
        "conformite_reglementaire",
        "Conformité réglementaire",
        "Identifier et respecter les contraintes légales, normatives ou sécuritaires",
    ),
]


# ── Seeds ─────────────────────────────────────────────────────────────────────


def seed_skills() -> None:
    """Insère les 10 skills V1.0 si absents. Idempotente (INSERT OR IGNORE sur slug UNIQUE)."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        for slug, label_fr, description in _SKILLS_SEED:
            conn.execute(
                "INSERT OR IGNORE INTO skills (slug, label_fr, description) VALUES (?, ?, ?)",
                (slug, label_fr, description),
            )
    conn.close()
    logger.info("seed_skills: %d skills disponibles", len(_SKILLS_SEED))


# ── Skills CRUD ───────────────────────────────────────────────────────────────


def get_all_skills() -> list[dict]:
    """Retourne tous les skills actifs, ordonnés par id."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, slug, label_fr, description FROM skills WHERE is_active = 1 ORDER BY id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_skill_by_slug(slug: str) -> Optional[dict]:
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, slug, label_fr, description, is_active FROM skills WHERE slug = ?",
            (slug,),
        ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── chunk_skills CRUD ─────────────────────────────────────────────────────────


def _upsert_chunk_skill(
    chunk_id: int,
    skill_id: int,
    weight: float,
    source: str = "keyword",
) -> None:
    """INSERT OR IGNORE — n'écrase jamais un mapping existant (règle additive stricte)."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO chunk_skills
                (chunk_id, skill_id, weight, source, is_validated, is_active)
            VALUES (?, ?, ?, ?, 0, 1)
            """,
            (chunk_id, skill_id, weight, source),
        )
    conn.close()


def get_chunk_skills(chunk_id: int) -> list[dict]:
    """Retourne les skills actifs associés à un chunk."""
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT cs.skill_id, cs.weight, cs.source, cs.is_validated,
                   s.slug, s.label_fr
            FROM chunk_skills cs
            JOIN skills s ON cs.skill_id = s.id
            WHERE cs.chunk_id = ? AND cs.is_active = 1 AND s.is_active = 1
            """,
            (chunk_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def classify_and_save_document_skills(document_id: int) -> dict:
    """
    Classifie par mots-clés les skills de tous les chunks d'un document.

    - INSERT OR IGNORE : n'écrase jamais un mapping existant.
    - Jamais bloquant : les erreurs par chunk sont loggées et ignorées.
    - Retourne un rapport {total_chunks, mapped_chunks, total_mappings}.
    """
    from engine.skill_mapper import classify_chunk_skills

    with sqlite3.connect(_db.DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, chunk_text FROM chunks WHERE document_id = ? AND char_count >= 50",
            (document_id,),
        ).fetchall()
    conn.close()

    if not rows:
        logger.info("classify_and_save_document_skills: doc %d — aucun chunk éligible", document_id)
        return {"total_chunks": 0, "mapped_chunks": 0, "total_mappings": 0}

    skill_index = {s["slug"]: s["id"] for s in get_all_skills()}
    if not skill_index:
        logger.warning(
            "classify_and_save_document_skills: table skills vide — seed manquant ?"
        )
        return {"total_chunks": len(rows), "mapped_chunks": 0, "total_mappings": 0}

    total_chunks   = len(rows)
    mapped_chunks  = 0
    total_mappings = 0

    for chunk_id, chunk_text in rows:
        try:
            proposals = classify_chunk_skills(chunk_text or "")
            for p in proposals:
                skill_id = skill_index.get(p["slug"])
                if skill_id is None:
                    continue
                _upsert_chunk_skill(chunk_id, skill_id, p["weight"])
                total_mappings += 1
            if proposals:
                mapped_chunks += 1
        except Exception as exc:
            logger.warning(
                "classify_and_save_document_skills: chunk %d ignoré : %s",
                chunk_id, exc,
            )

    logger.info(
        "classify_and_save_document_skills: doc %d — %d/%d chunks mappés, %d liens",
        document_id, mapped_chunks, total_chunks, total_mappings,
    )
    return {
        "total_chunks":   total_chunks,
        "mapped_chunks":  mapped_chunks,
        "total_mappings": total_mappings,
    }


# ── user_skill_mastery CRUD ───────────────────────────────────────────────────


def get_user_skill_mastery(user_id: str = "default") -> list[dict]:
    """
    Retourne les mastery scores de l'utilisateur, triés par score croissant
    (skills les plus fragiles en premier).
    """
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                s.slug,
                s.label_fr,
                s.description,
                usm.mastery_score,
                usm.attempts_count,
                usm.last_reviewed_at
            FROM user_skill_mastery usm
            JOIN skills s ON usm.skill_id = s.id
            WHERE usm.user_id = ? AND s.is_active = 1
            ORDER BY usm.mastery_score ASC
            """,
            (user_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_skill_mastery(user_id: str = "default") -> None:
    """
    Recalcule et persiste le mastery_score par skill pour un utilisateur.

    Aggrège les scores des tentatives sur tous les chunks associés à chaque skill.
    UPSERT (INSERT OR IGNORE + UPDATE) — jamais DELETE.
    """
    from engine.skill_engine import compute_skill_mastery

    with sqlite3.connect(_db.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT cs.skill_id, a.score
            FROM attempts a
            JOIN chunk_skills cs ON a.chunk_id = cs.chunk_id
            WHERE a.user_id  = ?
              AND a.score    IS NOT NULL
              AND a.chunk_id IS NOT NULL
              AND cs.is_active = 1
            """,
            (user_id,),
        ).fetchall()
    conn.close()

    if not rows:
        return

    skill_scores: dict[int, list[float]] = defaultdict(list)
    for skill_id, score in rows:
        skill_scores[skill_id].append(float(score))

    with sqlite3.connect(_db.DB_PATH) as conn:
        for skill_id, scores in skill_scores.items():
            mastery_score  = compute_skill_mastery(scores)
            attempts_count = len(scores)
            conn.execute(
                """
                INSERT OR IGNORE INTO user_skill_mastery
                    (user_id, skill_id, mastery_score, attempts_count,
                     last_reviewed_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (user_id, skill_id, mastery_score, attempts_count),
            )
            conn.execute(
                """
                UPDATE user_skill_mastery
                SET mastery_score    = ?,
                    attempts_count   = ?,
                    last_reviewed_at = CURRENT_TIMESTAMP,
                    updated_at       = CURRENT_TIMESTAMP
                WHERE user_id = ? AND skill_id = ?
                """,
                (mastery_score, attempts_count, user_id, skill_id),
            )
    conn.close()

    logger.info(
        "update_user_skill_mastery: user=%s — %d skill(s) mis à jour",
        user_id, len(skill_scores),
    )


# ── Remap V1.1 ────────────────────────────────────────────────────────────────


def remap_document_skills(document_id: int) -> dict:
    """
    Recalcule les mappings keyword pour tous les chunks d'un document.

    Règles strictes :
    - is_validated=1 → intouchable, jamais modifié.
    - Mapping existant source='keyword', is_validated=0 → UPDATE poids + is_active.
    - Nouveau skill détecté absent de chunk_skills → INSERT.
    - Mapping source='keyword', is_validated=0, skill non détecté → is_active=0 (soft-delete).

    Retourne {total_chunks, remapped_chunks, inserted, updated, deactivated}.
    """
    from engine.skill_mapper import classify_chunk_skills

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        chunk_rows = conn.execute(
            "SELECT id, chunk_text FROM chunks WHERE document_id = ? AND char_count >= 50",
            (document_id,),
        ).fetchall()

    if not chunk_rows:
        return {
            "total_chunks": 0, "remapped_chunks": 0,
            "inserted": 0, "updated": 0, "deactivated": 0,
        }

    skill_index = {s["slug"]: s["id"] for s in get_all_skills()}
    if not skill_index:
        logger.warning("remap_document_skills: table skills vide — seed manquant ?")
        return {
            "total_chunks": len(chunk_rows), "remapped_chunks": 0,
            "inserted": 0, "updated": 0, "deactivated": 0,
        }

    total_chunks  = len(chunk_rows)
    remapped      = 0
    inserted      = 0
    updated       = 0
    deactivated   = 0

    for row in chunk_rows:
        chunk_id   = row["id"]
        chunk_text = row["chunk_text"] or ""

        try:
            proposals = classify_chunk_skills(chunk_text)
            detected_skill_ids = {skill_index[p["slug"]]: p["weight"]
                                  for p in proposals if p["slug"] in skill_index}

            with sqlite3.connect(_db.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                existing = conn.execute(
                    """
                    SELECT skill_id, weight, source, is_validated, is_active
                    FROM chunk_skills
                    WHERE chunk_id = ?
                    """,
                    (chunk_id,),
                ).fetchall()
            conn.close()

            existing_by_skill = {r["skill_id"]: dict(r) for r in existing}

            with sqlite3.connect(_db.DB_PATH) as conn:
                # 1. Nouveaux skills détectés absents de chunk_skills → INSERT
                for skill_id, weight in detected_skill_ids.items():
                    if skill_id not in existing_by_skill:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO chunk_skills
                                (chunk_id, skill_id, weight, source, is_validated, is_active)
                            VALUES (?, ?, ?, 'keyword', 0, 1)
                            """,
                            (chunk_id, skill_id, weight),
                        )
                        inserted += 1

                # 2. Mappings existants source='keyword', is_validated=0
                for skill_id, rec in existing_by_skill.items():
                    if rec["is_validated"] == 1:
                        continue  # intouchable
                    if rec["source"] != "keyword":
                        continue  # on ne touche que les mappings auto

                    if skill_id in detected_skill_ids:
                        new_weight = detected_skill_ids[skill_id]
                        new_active = 1
                    else:
                        new_weight = rec["weight"]
                        new_active = 0

                    conn.execute(
                        """
                        UPDATE chunk_skills
                        SET weight    = ?,
                            is_active = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE chunk_id = ? AND skill_id = ?
                          AND is_validated = 0 AND source = 'keyword'
                        """,
                        (new_weight, new_active, chunk_id, skill_id),
                    )
                    if skill_id in detected_skill_ids:
                        updated += 1
                    else:
                        deactivated += 1
            conn.close()

            if detected_skill_ids:
                remapped += 1

        except Exception as exc:
            logger.warning(
                "remap_document_skills: chunk %d ignoré : %s", chunk_id, exc
            )

    logger.info(
        "remap_document_skills: doc %d — %d/%d chunks, +%d inserts, "
        "%d updates, %d désactivations",
        document_id, remapped, total_chunks, inserted, updated, deactivated,
    )
    return {
        "total_chunks":   total_chunks,
        "remapped_chunks": remapped,
        "inserted":       inserted,
        "updated":        updated,
        "deactivated":    deactivated,
    }


def remap_all_documents() -> dict:
    """
    Applique remap_document_skills à tous les documents de la base.

    Retourne un rapport agrégé {documents, total_chunks, inserted, updated, deactivated}.
    """
    with sqlite3.connect(_db.DB_PATH) as conn:
        doc_ids = [r[0] for r in conn.execute("SELECT id FROM documents ORDER BY id").fetchall()]
    conn.close()

    agg = {"documents": 0, "total_chunks": 0, "inserted": 0, "updated": 0, "deactivated": 0}

    for doc_id in doc_ids:
        try:
            r = remap_document_skills(doc_id)
            agg["documents"]     += 1
            agg["total_chunks"]  += r["total_chunks"]
            agg["inserted"]      += r["inserted"]
            agg["updated"]       += r["updated"]
            agg["deactivated"]   += r["deactivated"]
        except Exception as exc:
            logger.warning("remap_all_documents: doc %d ignoré : %s", doc_id, exc)

    logger.info(
        "remap_all_documents: %d docs — +%d inserts, %d updates, %d désactivations",
        agg["documents"], agg["inserted"], agg["updated"], agg["deactivated"],
    )
    return agg
