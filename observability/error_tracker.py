import json
import logging
import os
import threading
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_ERRORS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "logs", "errors.jsonl"
)
_lock = threading.Lock()
_recent: deque = deque(maxlen=100)


def track(error_type: str, message: str, context: str = "") -> None:
    """Enregistre une erreur en mémoire et dans logs/errors.jsonl."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": error_type,
        "msg": message[:200],
        "ctx": context[:100],
    }
    with _lock:
        _recent.append(entry)
    try:
        os.makedirs(os.path.dirname(_ERRORS_PATH), exist_ok=True)
        with open(_ERRORS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("error_tracker.track: écriture impossible (%s)", type(exc).__name__)


def get_recent(n: int = 10) -> list[dict]:
    """Retourne les n dernières erreurs tracées (ordre chronologique)."""
    with _lock:
        return list(_recent)[-n:]
