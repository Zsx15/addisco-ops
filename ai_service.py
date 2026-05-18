import json
import logging
import random
import struct
from typing import Optional

logger = logging.getLogger(__name__)

from ai_gateway.gateway import call_chat_completion, call_embedding_api
from database import (
    get_chunk_mastery,
    get_chunk_question_history,
    get_learning_profile,
)
from rag_service import search_similar_chunks, search_similar_chunks_multi
from adaptive_engine import (
    _MASTERY_BIAS,
    _PEDAGOGY_GROUPS as _PROFILE_TYPES,
    QUESTION_TYPES,
    _choose_question_type,
    explain_type_choice,
)

TEXT_MAX_CHARS = 6000

# text-embedding-3-small : 1 536 dimensions, ~8 000 tokens max en entrée
EMBEDDING_MODEL     = "text-embedding-3-small"
EMBEDDING_MAX_CHARS = 24_000  # ~8 000 tokens × 3 chars/token, marge de sécurité

# Nombre de chunks récupérés lors du retrieval RAG
RAG_TOP_K = 3


_TYPE_PROMPTS = {
    "question_directe": (
        "Génère une question directe de compréhension qui teste une notion clé du texte."
    ),
    "cas_pratique": (
        "Génère une question sous forme de cas pratique : décris une situation concrète "
        "et demande comment l'apprenant devrait réagir selon le texte."
    ),
    "vrai_faux": (
        "Génère une affirmation (vraie ou fausse) tirée du texte "
        "et demande à l'apprenant de dire si elle est correcte et de la justifier."
    ),
    "question_piege": (
        "Génère une question piège qui contient une erreur ou une nuance subtile "
        "que l'apprenant doit identifier et corriger."
    ),
    "reformulation": (
        "Demande à l'apprenant d'expliquer le concept principal du texte avec ses propres mots, "
        "sans utiliser les termes exacts du document."
    ),
    "consequence": (
        "Génère une question sur les conséquences, les conditions d'application "
        "ou les cas d'exclusion d'une règle ou d'un processus décrit dans le texte."
    ),
}


def _truncate(text: str) -> str:
    return text[:TEXT_MAX_CHARS] if len(text) > TEXT_MAX_CHARS else text


def _call_embedding_api(text: str) -> list[float]:
    """
    Délègue à ai_gateway.call_embedding_api avec troncature métier.
    Lève RuntimeError si le gateway retourne None (erreur API).
    """
    result = call_embedding_api(text[:EMBEDDING_MAX_CHARS])
    if result is None:
        raise RuntimeError("L'API embeddings a échoué.")
    return result


def generate_embedding(text: str) -> bytes:
    """
    Génère un embedding et retourne un BLOB (float32 little-endian) pour stockage SQLite.
    Lève une exception en cas d'échec — l'appelant gère la dégradation gracieuse.
    """
    vector = _call_embedding_api(text)
    return struct.pack(f"<{len(vector)}f", *vector)


def generate_question(
    source_text: str,
    document_id: Optional[int] = None,
    document_ids: Optional[list[int]] = None,
    user_id: str = "default",
) -> tuple[str, list[int], str]:
    """
    Génère une question de compréhension à partir du texte source.

    Retourne un tuple (question, chunk_ids, question_type) :
    - question      : str — la question générée
    - chunk_ids     : list[int] — IDs des chunks utilisés (vide si fallback)
    - question_type : str — type pédagogique utilisé (issu de QUESTION_TYPES)

    Variation pédagogique : le type est choisi par rotation sur l'historique
    du chunk primaire (chunk_ids[0]). En fallback texte brut, sélection aléatoire.
    Les 2 dernières questions posées sur ce chunk sont passées au LLM pour éviter
    les doublons.

    Adaptation profil : si un profil pédagogique existe pour user_id, le
    preferred_pedagogy est utilisé comme tie-breaker final après la rotation et
    le biais mastery. Absent ou None → comportement inchangé.
    """
    # ── Résolution du contexte ────────────────────────────────────────────────
    context   = _truncate(source_text)
    chunk_ids: list[int] = []

    if document_ids:
        try:
            query_vector = _call_embedding_api(source_text)
            chunks       = search_similar_chunks_multi(query_vector, document_ids, top_k=RAG_TOP_K)
            if chunks:
                context   = "\n\n---\n\n".join(c["chunk_text"] for c in chunks)
                chunk_ids = [c["id"] for c in chunks]
        except Exception:
            logger.warning("generate_question: RAG multi fallback (docs=%s)", document_ids)
    elif document_id is not None:
        try:
            query_vector = _call_embedding_api(source_text)
            chunks       = search_similar_chunks(query_vector, document_id, top_k=RAG_TOP_K)
            if chunks:
                context   = "\n\n---\n\n".join(c["chunk_text"] for c in chunks)
                chunk_ids = [c["id"] for c in chunks]
        except Exception:
            logger.warning("generate_question: RAG fallback (doc=%s)", document_id)

    # ── Choix du type pédagogique ─────────────────────────────────────────────
    history: list[dict] = []
    mastery_class: Optional[str] = None
    if chunk_ids:
        try:
            history = get_chunk_question_history(chunk_ids[0], limit=5, user_id=user_id)
        except Exception:
            pass
        try:
            mastery_class = get_chunk_mastery(chunk_ids[0], user_id=user_id)
        except Exception:
            pass

    # Biais profil : preferred_pedagogy → types associés (tie-breaker secondaire)
    profile_types: Optional[list[str]] = None
    try:
        profile = get_learning_profile(user_id)
        if profile and profile.get("preferred_pedagogy"):
            profile_types = _PROFILE_TYPES.get(profile["preferred_pedagogy"])
    except Exception:
        pass

    used_types    = [h["question_type"] for h in history if h.get("question_type")]
    question_type = _choose_question_type(
        used_types, mastery_class=mastery_class, profile_types=profile_types
    )
    logger.info(
        "generate_question: type=%s mastery=%s doc=%s user=%s",
        question_type, mastery_class, document_id, user_id,
    )
    type_instruction = _TYPE_PROMPTS[question_type]

    # Instructions anti-doublon : 2 dernières questions de ce chunk
    avoid_block = ""
    previous_qs = [h["question"] for h in history[:2] if h.get("question")]
    if previous_qs:
        lines       = "\n".join(f"- {q}" for q in previous_qs)
        avoid_block = (
            f"\n\nNe pose pas une question identique ou très similaire à :\n{lines}"
        )

    # ── Appel LLM ─────────────────────────────────────────────────────────────
    system_prompt = (
        f"Tu es un formateur expert. {type_instruction} "
        f"Réponds uniquement avec la question, sans introduction ni commentaire."
        f"{avoid_block}"
    )

    content = call_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Texte source :\n\n{context}"},
        ],
        task_type="question_generation",
        max_tokens=200,
        temperature=0.7,
    )
    if content is None:
        raise RuntimeError(
            "La génération de question a échoué. Vérifiez votre connexion ou réessayez."
        )

    return content.strip(), chunk_ids, question_type


_CORRECT_FALLBACK = {
    "score": 0.0,
    "expected_answer": "",
    "correction": "La correction est temporairement indisponible. Réessayez.",
    "error_type": "hors_sujet",
    "topic": "",
}


def correct_answer(question: str, user_answer: str, source_text: str) -> dict:
    content = call_chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un formateur expert qui corrige des réponses. "
                    "Réponds en JSON avec exactement ces champs :\n"
                    "- score : décimal entre 0.0 et 1.0\n"
                    "- expected_answer : réponse idéale concise\n"
                    "- correction : explication pédagogique en 2 à 4 phrases\n"
                    "- error_type : un de ces types si score < 0.8 : "
                    "oubli_etape | confusion_notion | reponse_vague | erreur_ordre | hors_sujet | correct\n"
                    "- topic : notion principale testée (3 à 5 mots)\n"
                    "Réponds uniquement avec le JSON brut, sans markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Texte source :\n{_truncate(source_text)}\n\n"
                    f"Question : {question}\n\n"
                    f"Réponse de l'apprenant : {user_answer}"
                ),
            },
        ],
        task_type="correction",
        max_tokens=400,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    if content is None:
        return dict(_CORRECT_FALLBACK)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("correct_answer: JSON decode error")
        return dict(_CORRECT_FALLBACK)

    return {
        "score":           float(data.get("score", 0.0)),
        "expected_answer": str(data.get("expected_answer", "")),
        "correction":      str(data.get("correction", "—")),
        "error_type":      str(data.get("error_type", "hors_sujet")),
        "topic":           str(data.get("topic", "")),
    }
