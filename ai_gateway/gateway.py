import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from ai_gateway.rate_limiter import check_rate_limit
from ai_gateway.request_logger import log_request
from db.runtime_metrics import record_metric

load_dotenv()

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def _get_gateway_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY manquante — configurez un fichier .env.")
        _client = OpenAI(api_key=api_key)
    return _client


def call_embedding_api(
    text: str,
    model: str = "text-embedding-3-small",
    user_id: str = "default",
) -> Optional[list[float]]:
    """
    Appel embeddings API. Retourne le vecteur float32 ou None en cas d'échec.
    La troncature du texte reste à la charge du caller (logique métier).
    user_id : identifiant pour le rate limiting par utilisateur.
    """
    allowed, reason = check_rate_limit(user_id, "embedding")
    if not allowed:
        logger.warning("gateway.call_embedding_api: rate limit [%s] %s", user_id, reason)
        return None

    client = _get_gateway_client()
    start = time.monotonic()
    success = False
    tokens_in: Optional[int] = None
    error_type: Optional[str] = None
    cost: Optional[float] = None

    try:
        response = client.embeddings.create(model=model, input=text)
        vector = response.data[0].embedding
        success = True
        if response.usage:
            tokens_in = response.usage.total_tokens
            # text-embedding-3-small : $0.02 / 1M tokens
            cost = round(tokens_in * 0.00000002, 8)
        return vector
    except Exception as exc:
        error_type = type(exc).__name__
        logger.error("gateway.call_embedding_api: %s", error_type)
        return None
    finally:
        elapsed = time.monotonic() - start
        log_request(task_type="embedding", duration=elapsed, success=success)
        record_metric(
            metric_type="embedding",
            endpoint="call_embedding_api",
            latency_ms=round(elapsed * 1000),
            estimated_cost=cost,
            tokens_input=tokens_in,
            success=success,
            fallback_used=False,
            error_type=error_type,
            user_id=user_id,
        )


def call_chat_completion(
    messages: list[dict],
    task_type: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 400,
    temperature: float = 0.7,
    response_format: Optional[dict] = None,
    timeout: int = 30,
    user_id: str = "default",
) -> Optional[str]:
    """
    Point d'entrée unique pour les appels chat completions.
    Retourne le contenu texte de la réponse, ou None en cas d'échec.
    Le caller reste responsable de la logique métier (fallback, parsing JSON, etc.).
    user_id : identifiant pour le rate limiting par utilisateur.
    """
    allowed, reason = check_rate_limit(user_id, "chat")
    if not allowed:
        logger.warning("gateway.call_chat_completion [%s]: rate limit [%s] %s", task_type, user_id, reason)
        return None

    client = _get_gateway_client()
    start = time.monotonic()
    success = False
    fallback_used = False
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    error_type: Optional[str] = None
    cost: Optional[float] = None

    try:
        kwargs: dict = dict(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        content = (
            response.choices[0].message.content
            if response.choices
            else None
        )
        # Normalise contenu vide en None — le caller ne doit pas recevoir ""
        if not content:
            content = None
        success = content is not None
        # Réponse vide sans exception = fallback implicite
        fallback_used = not success

        if getattr(response, "usage", None):
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens
            # gpt-4o-mini : $0.15/1M input + $0.60/1M output
            cost = round(tokens_in * 0.00000015 + tokens_out * 0.0000006, 8)

        return content

    except Exception as exc:
        error_type = type(exc).__name__
        fallback_used = True
        logger.error(
            "gateway.call_chat_completion [%s]: %s", task_type, error_type
        )
        return None

    finally:
        elapsed = time.monotonic() - start
        log_request(task_type=task_type, duration=elapsed, success=success)
        record_metric(
            metric_type="chat",
            endpoint=task_type,
            latency_ms=round(elapsed * 1000),
            estimated_cost=cost,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            success=success,
            fallback_used=fallback_used,
            error_type=error_type,
            user_id=user_id,
        )
