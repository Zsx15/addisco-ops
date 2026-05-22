"""
ai_gateway/rate_limiter.py

Rate limiter in-memory, sliding window, par utilisateur et type d'appel.
Thread-safe — stdlib uniquement (threading, time, collections).
Aucune dépendance externe, aucun accès base de données.

Limites configurables via variables d'environnement :
  RATE_CHAT_PER_MINUTE  (défaut : 20)
  RATE_CHAT_PER_HOUR    (défaut : 200)
  RATE_EMBED_PER_MINUTE (défaut : 30)
  RATE_EMBED_PER_HOUR   (défaut : 500)

Comportement quand la limite est atteinte :
  check() retourne (False, reason_str) — le caller décide de la réaction.
  Le gateway logue un WARNING et retourne None, cohérent avec les erreurs API.
"""
import os
import threading
import time
from collections import deque
from typing import Optional

# ── Limites par type d'appel ───────────────────────────────────────────────────

_LIMITS: dict[str, dict[str, int]] = {
    "chat": {
        "per_minute": int(os.getenv("RATE_CHAT_PER_MINUTE", "20")),
        "per_hour":   int(os.getenv("RATE_CHAT_PER_HOUR",   "200")),
    },
    "embedding": {
        "per_minute": int(os.getenv("RATE_EMBED_PER_MINUTE", "30")),
        "per_hour":   int(os.getenv("RATE_EMBED_PER_HOUR",   "500")),
    },
}


# ── Sliding window ─────────────────────────────────────────────────────────────


class _SlidingWindow:
    """
    Compteur à fenêtre glissante thread-safe.
    Conserve les timestamps des appels sur 1h maximum.
    """

    def __init__(self, per_minute: int, per_hour: int) -> None:
        self._per_minute = per_minute
        self._per_hour   = per_hour
        self._lock       = threading.Lock()
        self._calls: deque[float] = deque()

    def check_and_record(self) -> tuple[bool, str]:
        """
        Vérifie si un appel est autorisé et l'enregistre si oui.
        Retourne (allowed: bool, reason: str).
        """
        now = time.monotonic()
        with self._lock:
            # Purge des timestamps > 1 heure
            cutoff_hour = now - 3600.0
            while self._calls and self._calls[0] < cutoff_hour:
                self._calls.popleft()

            hour_count = len(self._calls)
            if hour_count >= self._per_hour:
                return False, f"limite/heure atteinte ({hour_count}/{self._per_hour})"

            # Compte dans la fenêtre de 60 secondes
            cutoff_min   = now - 60.0
            minute_count = sum(1 for t in self._calls if t >= cutoff_min)
            if minute_count >= self._per_minute:
                return False, f"limite/minute atteinte ({minute_count}/{self._per_minute})"

            self._calls.append(now)
            return True, ""

    def reset(self) -> None:
        """Vide le compteur — utilisé par les tests et les outils admin."""
        with self._lock:
            self._calls.clear()

    @property
    def call_count_last_minute(self) -> int:
        """Nombre d'appels dans la dernière minute — pour les tests et le monitoring."""
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            return sum(1 for t in self._calls if t >= cutoff)

    @property
    def call_count_last_hour(self) -> int:
        """Nombre d'appels dans la dernière heure."""
        with self._lock:
            return len(self._calls)


# ── Rate limiter global ────────────────────────────────────────────────────────


class _RateLimiter:
    """
    Gère les compteurs par (user_id, call_type).
    call_type attendu : "chat" | "embedding".
    """

    def __init__(self) -> None:
        self._lock    = threading.Lock()
        self._windows: dict[tuple[str, str], _SlidingWindow] = {}

    def _get_window(self, user_id: str, call_type: str) -> _SlidingWindow:
        key = (user_id, call_type)
        with self._lock:
            if key not in self._windows:
                limits = _LIMITS.get(call_type, _LIMITS["chat"])
                self._windows[key] = _SlidingWindow(
                    per_minute=limits["per_minute"],
                    per_hour=limits["per_hour"],
                )
            return self._windows[key]

    def check(self, user_id: str, call_type: str) -> tuple[bool, str]:
        """Retourne (allowed: bool, reason: str)."""
        return self._get_window(user_id, call_type).check_and_record()

    def reset(
        self,
        user_id:   Optional[str] = None,
        call_type: Optional[str] = None,
    ) -> None:
        """
        Réinitialise les compteurs.
        user_id=None → tous les utilisateurs.
        call_type=None → tous les types.
        """
        with self._lock:
            if user_id is None:
                for w in self._windows.values():
                    w.reset()
            else:
                for (uid, ct), w in self._windows.items():
                    if uid == user_id and (call_type is None or ct == call_type):
                        w.reset()

    def get_window(self, user_id: str, call_type: str) -> _SlidingWindow:
        """Expose la fenêtre pour les tests et le monitoring."""
        return self._get_window(user_id, call_type)


# Singleton module-level — partagé par tous les appels du processus
_limiter = _RateLimiter()


# ── API publique ───────────────────────────────────────────────────────────────


def check_rate_limit(user_id: str, call_type: str) -> tuple[bool, str]:
    """
    Vérifie et enregistre un appel API.

    Args:
        user_id   : identifiant de l'utilisateur (ex : "default")
        call_type : "chat" ou "embedding"

    Returns:
        (True, "")           — appel autorisé
        (False, reason_str)  — limite atteinte
    """
    return _limiter.check(user_id, call_type)


def reset_rate_limiter(
    user_id:   Optional[str] = None,
    call_type: Optional[str] = None,
) -> None:
    """
    Réinitialise les compteurs du rate limiter.
    Destiné aux tests et aux outils admin — pas au code de production.
    """
    _limiter.reset(user_id, call_type)


def get_rate_limit_window(user_id: str, call_type: str) -> _SlidingWindow:
    """Retourne la fenêtre interne — pour tests et monitoring uniquement."""
    return _limiter.get_window(user_id, call_type)
