import json
import logging
import os
import random
import struct
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

from database import (
    get_chunk_mastery,
    get_chunk_question_history,
    get_learning_profile,
)
from rag_service import search_similar_chunks
from adaptive_engine import _MASTERY_BIAS, _PEDAGOGY_GROUPS as _PROFILE_TYPES, QUESTION_TYPES

load_dotenv()

_client: Optional[OpenAI] = None

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


def _choose_question_type(
    used_types: list[str],
    mastery_class: Optional[str] = None,
    profile_types: Optional[list[str]] = None,
) -> str:
    """
    Choisit le type de question le moins utilisé pour ce chunk.

    Priorités décroissantes :
    1. Rotation équitable (type le moins posé sur ce chunk).
    2. Biais mastery (Fragile/Maîtrisé) parmi les candidats équitables.
    3. Biais profil utilisateur (preferred_pedagogy) comme tie-breaker final.

    Chaque niveau ne s'applique que si son ensemble candidat est non vide,
    garantissant que l'absence de signal ne dégrade jamais le comportement.
    """
    if not used_types:
        bias = _MASTERY_BIAS.get(mastery_class or "", [])
        pool = bias if bias else QUESTION_TYPES
        if profile_types:
            matched = [t for t in profile_types if t in pool]
            if matched:
                return random.choice(matched)
        return random.choice(pool)

    counts     = {t: used_types.count(t) for t in QUESTION_TYPES}
    min_count  = min(counts.values())
    candidates = [t for t, c in counts.items() if c == min_count]
    bias       = _MASTERY_BIAS.get(mastery_class or "", [])
    biased     = [t for t in bias if t in candidates]
    pool       = biased if biased else candidates
    if profile_types:
        matched = [t for t in profile_types if t in pool]
        if matched:
            return random.choice(matched)
    return random.choice(pool)


def explain_type_choice(
    used_types: list[str],
    mastery_class: Optional[str],
    profile_pedagogy: Optional[str],
    chosen_type: str,
) -> str:
    """
    Retourne une explication textuelle de la décision de sélection du type de question.
    Miroir narratif de _choose_question_type() — fonction additive, ne modifie pas le moteur.
    Aucun appel API.
    """
    _type_fr: dict[str, str] = {
        "question_directe": "question directe",
        "cas_pratique":     "cas pratique",
        "vrai_faux":        "vrai / faux",
        "question_piege":   "question piège",
        "reformulation":    "reformulation",
        "consequence":      "conséquence",
    }
    _mastery_fr: dict[str, str] = {
        "Fragile":          "Fragile",
        "En consolidation": "En consolidation",
        "Maîtrisé":         "Maîtrisé",
    }
    _profile_fr: dict[str, str] = {
        "logical":    "analytique",
        "procedural": "procédural",
        "narrative":  "narratif",
        "analogy":    "analogique",
    }

    chosen_fr = _type_fr.get(chosen_type, chosen_type)

    if not used_types:
        if mastery_class and mastery_class in _MASTERY_BIAS:
            mc_fr = _mastery_fr.get(mastery_class, mastery_class)
            return f"Premier type sur cette section — biais {mc_fr} appliqué ({chosen_fr})"
        return f"Premier type sur cette section — sélection initiale ({chosen_fr})"

    counts     = {t: used_types.count(t) for t in QUESTION_TYPES}
    min_count  = min(counts.values())
    candidates = [t for t, c in counts.items() if c == min_count]
    bias       = _MASTERY_BIAS.get(mastery_class or "", [])
    biased     = [t for t in bias if t in candidates]

    profile_types = _PROFILE_TYPES.get(profile_pedagogy or "", []) if profile_pedagogy else []

    if biased and chosen_type in biased:
        mc_fr = _mastery_fr.get(mastery_class or "", mastery_class or "")
        if profile_types and chosen_type in profile_types:
            pf_fr = _profile_fr.get(profile_pedagogy or "", profile_pedagogy or "")
            return f"Sélectionné par biais maîtrise ({mc_fr}) et profil {pf_fr} ({chosen_fr})"
        return f"Sélectionné par biais maîtrise ({mc_fr} → {chosen_fr} priorisé)"

    if profile_types and chosen_type in profile_types and chosen_type in candidates:
        pf_fr = _profile_fr.get(profile_pedagogy or "", profile_pedagogy or "")
        return f"Sélectionné par profil pédagogique ({pf_fr} → {chosen_fr} favorisé)"

    return f"Sélectionné par rotation équitable ({chosen_fr} le moins utilisé sur cette section)"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY manquante. Créez un fichier .env avec votre clé API."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def _truncate(text: str) -> str:
    return text[:TEXT_MAX_CHARS] if len(text) > TEXT_MAX_CHARS else text


def _call_embedding_api(text: str) -> list[float]:
    """
    Appel brut à l'API OpenAI embeddings — retourne le vecteur de floats.

    Ce helper existe pour séparer deux usages distincts du même appel API :
    - generate_embedding() en a besoin pour sérialiser et stocker en SQLite (→ bytes) ;
    - generate_question() en a besoin pour chercher des chunks similaires (→ list[float]).
    Factoriser ici évite de dupliquer la logique d'appel et de troncature.
    """
    client   = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text[:EMBEDDING_MAX_CHARS],
    )
    return response.data[0].embedding  # list[float], 1 536 dimensions


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
    client = _get_client()

    # ── Résolution du contexte ────────────────────────────────────────────────
    context   = _truncate(source_text)
    chunk_ids: list[int] = []

    if document_id is not None:
        try:
            query_vector = _call_embedding_api(source_text)
            chunks       = search_similar_chunks(query_vector, document_id, top_k=RAG_TOP_K)
            if chunks:
                context   = "\n\n---\n\n".join(c["chunk_text"] for c in chunks)
                chunk_ids = [c["id"] for c in chunks]
        except Exception:
            logger.warning("generate_question: RAG fallback (doc=%s)", document_id)
            pass

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Texte source :\n\n{context}"},
        ],
        max_tokens=200,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip(), chunk_ids, question_type


def correct_answer(question: str, user_answer: str, source_text: str) -> dict:
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
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
        max_tokens=400,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        logger.warning("correct_answer: JSON decode error")
        return {
            "score": 0.0,
            "expected_answer": "",
            "correction": "Erreur lors de l'analyse de la correction. Réessayez.",
            "error_type": "hors_sujet",
            "topic": "",
        }
