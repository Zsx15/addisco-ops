import json
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_METRICS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "logs", "metrics.json"
)
_lock = threading.Lock()

_counters: dict[str, int] = defaultdict(int)
_timings: dict[str, list[float]] = defaultdict(list)
_MAX_TIMING_SAMPLES = 1000


def increment(key: str, amount: int = 1) -> None:
    with _lock:
        _counters[key] += amount


def record_timing(key: str, duration_ms: float) -> None:
    with _lock:
        buf = _timings[key]
        buf.append(round(duration_ms, 1))
        if len(buf) > _MAX_TIMING_SAMPLES:
            _timings[key] = buf[-_MAX_TIMING_SAMPLES:]


def get_summary() -> dict:
    with _lock:
        return {
            "counters": dict(_counters),
            "avg_ms": {
                k: round(sum(v) / len(v), 1) if v else 0.0
                for k, v in _timings.items()
            },
        }


def flush_to_disk() -> None:
    """Persiste les métriques en cours dans logs/metrics.json."""
    try:
        os.makedirs(os.path.dirname(_METRICS_PATH), exist_ok=True)
        data = get_summary()
        data["flushed_at"] = datetime.now(timezone.utc).isoformat()
        with open(_METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.warning("metrics.flush_to_disk: %s", type(exc).__name__)
