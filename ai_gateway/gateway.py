import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from ai_gateway.request_logger import log_request

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


def call_chat_completion(
    messages: list[dict],
    task_type: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 400,
    temperature: float = 0.7,
    response_format: Optional[dict] = None,
    timeout: int = 30,
) -> Optional[str]:
    """
    Point d'entrée unique pour les appels chat completions.

    Retourne le contenu texte de la réponse, ou None en cas d'échec.
    Le caller reste responsable de la logique métier (fallback, parsing JSON, etc.).

    Usage prévu (migration progressive depuis ai_service.py) :
        content = call_chat_completion(messages, task_type="question_generation")
    """
    client = _get_gateway_client()
    start = time.monotonic()
    success = False

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
        success = content is not None
        return content

    except Exception as exc:
        logger.error(
            "gateway.call_chat_completion [%s]: %s", task_type, type(exc).__name__
        )
        return None

    finally:
        log_request(
            task_type=task_type,
            duration=time.monotonic() - start,
            success=success,
        )
