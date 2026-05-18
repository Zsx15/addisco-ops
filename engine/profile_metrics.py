"""Métriques dynamiques du profil utilisateur — momentum, vélocité, régularité."""
from datetime import datetime, timedelta


def compute_momentum(rows: list[tuple[str, float]], window_days: int = 7) -> float:
    """
    Momentum = avg_score(derniers window_days jours) − avg_score(fenêtre précédente).
    Mesure l'accélération récente. Retourne 0.0 si l'un des deux intervalles est vide.
    Borné à [−1.0, 1.0].
    """
    if not rows:
        return 0.0
    now           = datetime.now()
    cutoff_recent = now - timedelta(days=window_days)
    cutoff_prev   = now - timedelta(days=window_days * 2)
    recent_scores: list[float] = []
    prev_scores:   list[float] = []
    for created_at, score in rows:
        try:
            dt = datetime.fromisoformat(str(created_at))
        except (ValueError, TypeError):
            continue
        if score is None:
            continue
        if dt >= cutoff_recent:
            recent_scores.append(float(score))
        elif dt >= cutoff_prev:
            prev_scores.append(float(score))
    if not recent_scores or not prev_scores:
        return 0.0
    delta = (sum(recent_scores) / len(recent_scores)) - (sum(prev_scores) / len(prev_scores))
    return round(max(-1.0, min(1.0, delta)), 3)


def compute_learning_velocity(rows: list[tuple[str, float]]) -> float:
    """
    Vélocité = moyenne des deltas avg_score inter-sessions (une session = un jour).
    Retourne 0.0 si moins de 2 jours d'activité. Borné à [−1.0, 1.0].
    """
    if not rows:
        return 0.0
    day_scores: dict[str, list[float]] = {}
    for created_at, score in rows:
        try:
            dt = datetime.fromisoformat(str(created_at))
        except (ValueError, TypeError):
            continue
        if score is None:
            continue
        day_scores.setdefault(dt.strftime("%Y-%m-%d"), []).append(float(score))
    if len(day_scores) < 2:
        return 0.0
    avgs     = [sum(day_scores[d]) / len(day_scores[d]) for d in sorted(day_scores)]
    deltas   = [avgs[i + 1] - avgs[i] for i in range(len(avgs) - 1)]
    velocity = sum(deltas) / len(deltas)
    return round(max(-1.0, min(1.0, velocity)), 3)


def compute_consistency_score(rows: list[tuple[str, float]], window_days: int = 30) -> float:
    """
    Régularité = jours actifs / window_days sur les derniers window_days jours.
    Retourne 0.0 si aucune session dans la fenêtre. Borné à [0.0, 1.0].
    """
    if not rows or window_days <= 0:
        return 0.0
    cutoff      = datetime.now() - timedelta(days=window_days)
    active_days: set[str] = set()
    for created_at, score in rows:
        try:
            dt = datetime.fromisoformat(str(created_at))
        except (ValueError, TypeError):
            continue
        if score is None:
            continue
        if dt >= cutoff:
            active_days.add(dt.strftime("%Y-%m-%d"))
    if not active_days:
        return 0.0
    return round(len(active_days) / window_days, 3)
