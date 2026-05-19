"""Debug pédagogique skills — lecture seule stricte, aucun write SQL."""
import logging
from typing import Optional

from engine.skill_keywords import SKILL_KEYWORDS
from engine.skill_mapper import keyword_match_score

logger = logging.getLogger(__name__)

_SCORE_DIVISOR: int = 3


def explain_skill_detection(chunk_text: str) -> list[dict]:
    """
    Analyse pure d'un texte : retourne les skills détectés avec détail complet.

    Lecture seule. Aucun accès base de données.

    Retourne une liste de :
    {
      "slug"             : slug du skill,
      "keywords_matched" : liste des keywords trouvés,
      "weight"           : score calculé [0.0, 1.0],
      "collision_with"   : slugs des autres skills aussi détectés,
    }
    """
    if not chunk_text or not chunk_text.strip():
        return []

    text_lower = chunk_text.lower()
    raw: dict[str, dict] = {}

    for slug, keywords in SKILL_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in text_lower]
        if matched:
            weight = round(min(len(matched) / _SCORE_DIVISOR, 1.0), 3)
            raw[slug] = {"keywords_matched": matched, "weight": weight}

    detected_slugs = list(raw.keys())
    results = []
    for slug, data in raw.items():
        results.append({
            "slug":             slug,
            "keywords_matched": data["keywords_matched"],
            "weight":           data["weight"],
            "collision_with":   [s for s in detected_slugs if s != slug],
        })

    return sorted(results, key=lambda x: x["weight"], reverse=True)


def explain_chunk_skills(chunk_id: int) -> dict:
    """
    Retourne l'état DB + l'analyse live par keywords pour un chunk donné.

    Lecture seule. N'écrit rien en base.
    Utilise un import tardif de database pour compatibilité tests.
    """
    import sqlite3
    import database as _db

    # Fetch chunk + document
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        chunk_row = conn.execute(
            """
            SELECT c.id, c.chunk_text, c.section_title, c.chunk_index,
                   d.title AS document_title
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.id = ?
            """,
            (chunk_id,),
        ).fetchone()

        if not chunk_row:
            return {"error": f"Chunk {chunk_id} introuvable"}

        chunk = dict(chunk_row)

        # Mappings stockés en base (tous états)
        stored_rows = conn.execute(
            """
            SELECT cs.skill_id, cs.weight, cs.source, cs.is_validated,
                   cs.is_active, s.slug, s.label_fr
            FROM chunk_skills cs
            JOIN skills s ON cs.skill_id = s.id
            WHERE cs.chunk_id = ?
            ORDER BY cs.is_active DESC, cs.weight DESC
            """,
            (chunk_id,),
        ).fetchall()

    stored = [dict(r) for r in stored_rows]
    stored_active_slugs = {r["slug"] for r in stored if r["is_active"]}

    # Analyse live avec keywords actuels
    live = explain_skill_detection(chunk.get("chunk_text") or "")
    live_slugs = {r["slug"] for r in live}

    # Écarts entre stocké et live
    discrepancies = []
    for slug in live_slugs - stored_active_slugs:
        discrepancies.append({
            "slug":   slug,
            "type":   "non_mappé",
            "raison": "Détecté avec les keywords V1.1 mais absent de chunk_skills",
        })
    for slug in stored_active_slugs - live_slugs:
        discrepancies.append({
            "slug":   slug,
            "type":   "mapping_obsolète",
            "raison": "Présent en base mais keywords V1.1 ne le détectent plus",
        })

    return {
        "chunk_id":       chunk_id,
        "section_title":  chunk.get("section_title"),
        "document_title": chunk.get("document_title"),
        "text_preview":   (chunk.get("chunk_text") or "")[:250],
        "stored_mappings": stored,
        "live_detection":  live,
        "discrepancies":   discrepancies,
    }
