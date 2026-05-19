"""Analytics descriptifs des skills — lecture seule stricte, aucun write SQL."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_skill_frequency(document_id: Optional[int] = None) -> list[dict]:
    """
    Nombre de chunks mappés par skill.

    Retourne [{slug, label_fr, chunk_count, avg_weight}] trié par chunk_count DESC.
    Filtre optionnel par document_id.
    """
    import sqlite3
    import database as _db

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if document_id is not None:
            rows = conn.execute(
                """
                SELECT s.slug, s.label_fr,
                       COUNT(cs.id)       AS chunk_count,
                       ROUND(AVG(cs.weight), 3) AS avg_weight
                FROM chunk_skills cs
                JOIN skills s ON cs.skill_id = s.id
                JOIN chunks  c ON cs.chunk_id = c.id
                WHERE cs.is_active = 1
                  AND c.document_id = ?
                GROUP BY s.id
                ORDER BY chunk_count DESC
                """,
                (document_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT s.slug, s.label_fr,
                       COUNT(cs.id)       AS chunk_count,
                       ROUND(AVG(cs.weight), 3) AS avg_weight
                FROM chunk_skills cs
                JOIN skills s ON cs.skill_id = s.id
                WHERE cs.is_active = 1
                GROUP BY s.id
                ORDER BY chunk_count DESC
                """
            ).fetchall()

    return [dict(r) for r in rows]


def get_skill_collisions() -> list[dict]:
    """
    Paires de skills fréquemment co-détectés sur le même chunk.

    Retourne [{slug_a, slug_b, co_occurrence_count}] trié par co_occurrence_count DESC.
    Limité aux 20 premières paires pour éviter N² coûteux.
    """
    import sqlite3
    import database as _db

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT sa.slug AS slug_a, sb.slug AS slug_b,
                   COUNT(*) AS co_occurrence_count
            FROM chunk_skills csa
            JOIN chunk_skills csb ON csa.chunk_id = csb.chunk_id
                                  AND csa.skill_id < csb.skill_id
            JOIN skills sa ON csa.skill_id = sa.id
            JOIN skills sb ON csb.skill_id = sb.id
            WHERE csa.is_active = 1 AND csb.is_active = 1
            GROUP BY sa.id, sb.id
            ORDER BY co_occurrence_count DESC
            LIMIT 20
            """
        ).fetchall()

    return [dict(r) for r in rows]


def get_unused_skills() -> list[dict]:
    """
    Skills sans aucun mapping actif dans chunk_skills.

    Retourne [{slug, label_fr}].
    """
    import sqlite3
    import database as _db

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT s.slug, s.label_fr
            FROM skills s
            WHERE s.is_active = 1
              AND NOT EXISTS (
                  SELECT 1 FROM chunk_skills cs
                  WHERE cs.skill_id = s.id AND cs.is_active = 1
              )
            ORDER BY s.slug
            """
        ).fetchall()

    return [dict(r) for r in rows]


def get_overrepresented_skills(threshold_pct: float = 0.7) -> list[dict]:
    """
    Skills présents sur plus de `threshold_pct` (défaut 70 %) des chunks totaux.

    Retourne [{slug, label_fr, chunk_count, total_chunks, coverage_pct}].
    """
    import sqlite3
    import database as _db

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total_row = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
        total_chunks = total_row["n"] if total_row else 0

        if total_chunks == 0:
            return []

        rows = conn.execute(
            """
            SELECT s.slug, s.label_fr,
                   COUNT(DISTINCT cs.chunk_id) AS chunk_count
            FROM chunk_skills cs
            JOIN skills s ON cs.skill_id = s.id
            WHERE cs.is_active = 1
            GROUP BY s.id
            """
        ).fetchall()

    results = []
    for r in rows:
        coverage = round(r["chunk_count"] / total_chunks, 3)
        if coverage >= threshold_pct:
            results.append({
                "slug":          r["slug"],
                "label_fr":      r["label_fr"],
                "chunk_count":   r["chunk_count"],
                "total_chunks":  total_chunks,
                "coverage_pct":  coverage,
            })

    return sorted(results, key=lambda x: x["coverage_pct"], reverse=True)


def get_chunks_without_skills(document_id: Optional[int] = None) -> list[dict]:
    """
    Chunks sans aucun mapping actif dans chunk_skills.

    Retourne [{chunk_id, chunk_index, section_title, document_title, text_preview}].
    Filtre optionnel par document_id.
    """
    import sqlite3
    import database as _db

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if document_id is not None:
            rows = conn.execute(
                """
                SELECT c.id AS chunk_id, c.chunk_index, c.section_title,
                       d.title AS document_title,
                       SUBSTR(c.chunk_text, 1, 200) AS text_preview
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.document_id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM chunk_skills cs
                      WHERE cs.chunk_id = c.id AND cs.is_active = 1
                  )
                ORDER BY c.chunk_index
                """,
                (document_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.id AS chunk_id, c.chunk_index, c.section_title,
                       d.title AS document_title,
                       SUBSTR(c.chunk_text, 1, 200) AS text_preview
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM chunk_skills cs
                    WHERE cs.chunk_id = c.id AND cs.is_active = 1
                )
                ORDER BY d.id, c.chunk_index
                """
            ).fetchall()

    return [dict(r) for r in rows]


def estimate_skill_discrimination() -> list[dict]:
    """
    Estimation de la discrimination pédagogique de chaque skill.

    discrimination_score = 1.0 - coverage_pct
    Un score élevé = skill rare = bon discriminant pédagogique.
    Un score bas = skill ubiquitaire = faible valeur de ciblage.

    Retourne [{slug, label_fr, chunk_count, total_chunks, coverage_pct,
               discrimination_score}] trié par discrimination_score DESC.
    """
    import sqlite3
    import database as _db

    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total_row = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
        total_chunks = total_row["n"] if total_row else 0

        if total_chunks == 0:
            return []

        rows = conn.execute(
            """
            SELECT s.slug, s.label_fr,
                   COUNT(DISTINCT cs.chunk_id) AS chunk_count
            FROM chunk_skills cs
            JOIN skills s ON cs.skill_id = s.id
            WHERE cs.is_active = 1
            GROUP BY s.id
            """
        ).fetchall()

    results = []
    for r in rows:
        coverage = round(r["chunk_count"] / total_chunks, 3)
        results.append({
            "slug":                 r["slug"],
            "label_fr":             r["label_fr"],
            "chunk_count":          r["chunk_count"],
            "total_chunks":         total_chunks,
            "coverage_pct":         coverage,
            "discrimination_score": round(1.0 - coverage, 3),
        })

    return sorted(results, key=lambda x: x["discrimination_score"], reverse=True)
