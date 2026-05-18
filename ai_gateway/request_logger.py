import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "logs", "ai_requests.jsonl"
)


def log_request(task_type: str, duration: float, success: bool) -> None:
    """Appende une entrée JSON dans logs/ai_requests.jsonl."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task": task_type,
        "duration_ms": round(duration * 1000),
        "ok": success,
    }
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("request_logger: écriture impossible (%s)", type(exc).__name__)
