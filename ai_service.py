import json
import os
import struct

from dotenv import load_dotenv
from openai import OpenAI

from database import search_similar_chunks

load_dotenv()

_client: OpenAI | None = None

TEXT_MAX_CHARS = 6000

# text-embedding-3-small : 1 536 dimensions, ~8 000 tokens max en entrée
EMBEDDING_MODEL     = "text-embedding-3-small"
EMBEDDING_MAX_CHARS = 24_000  # ~8 000 tokens × 3 chars/token, marge de sécurité

# Nombre de chunks récupérés lors du retrieval RAG
RAG_TOP_K = 3


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
    source_text: str, document_id: int | None = None
) -> tuple[str, list[int]]:
    """
    Génère une question de compréhension à partir du texte source.

    Retourne un tuple (question, chunk_ids) :
    - question   : str — la question générée
    - chunk_ids  : list[int] — IDs des chunks utilisés pour le contexte RAG,
                   vide [] si fallback texte brut (document_id absent, embeddings
                   manquants, ou erreur API).

    Chemin fallback : texte brut tronqué → LLM. chunk_ids = [].
    Chemin RAG      : top-k chunks → LLM. chunk_ids contient leurs IDs.
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
            # Fallback silencieux — context et chunk_ids restent inchangés
            pass

    # ── Appel LLM — prompt identique quel que soit le chemin ────────────────
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un formateur expert. À partir du texte fourni, génère une seule question "
                    "de compréhension précise qui teste une notion clé. "
                    "Réponds uniquement avec la question, sans introduction."
                ),
            },
            {
                "role": "user",
                "content": f"Texte source :\n\n{context}",
            },
        ],
        max_tokens=200,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip(), chunk_ids


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
        return {
            "score": 0.0,
            "expected_answer": "",
            "correction": "Erreur lors de l'analyse de la correction. Réessayez.",
            "error_type": "hors_sujet",
            "topic": "",
        }
