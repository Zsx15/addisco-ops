"""Métriques de rétention pédagogique — fenêtres J+1, J+7, J+30."""
from datetime import datetime
from typing import Optional

_RETENTION_WINDOWS: dict[str, tuple[float, float]] = {
    "j1":  (0.5,  2.5),   # 12h–60h  — révision lendemain
    "j7":  (4.0, 10.0),   # 4–10j    — révision hebdomadaire
    "j30": (21.0, 45.0),  # 21–45j   — révision mensuelle
}


def compute_retention_metrics(
    rows: list[tuple[int, str, float]],
) -> dict[str, Optional[float]]:
    """
    Mesure la rétention sur 3 fenêtres temporelles.

    rows : liste de (chunk_id, created_at_iso, score).
    Méthode : groupe par chunk_id, paires consécutives dont l'écart tombe
    dans une fenêtre → collecte le score de révision. Résultat = moyenne.

    Retourne {"retention_j1": float|None, "retention_j7": float|None,
              "retention_j30": float|None}.
    None = aucune paire trouvée dans cette fenêtre.
    """
    if not rows:
        return {"retention_j1": None, "retention_j7": None, "retention_j30": None}

    by_chunk: dict[int, list[tuple[datetime, float]]] = {}
    for chunk_id, created_at_iso, score in rows:
        if score is None:
            continue
        try:
            dt  = datetime.fromisoformat(str(created_at_iso))
            cid = int(chunk_id)
        except (ValueError, TypeError):
            continue
        by_chunk.setdefault(cid, []).append((dt, float(score)))

    buckets: dict[str, list[float]] = {"j1": [], "j7": [], "j30": []}

    for attempts in by_chunk.values():
        attempts.sort(key=lambda x: x[0])
        for i in range(len(attempts) - 1):
            dt_a, _   = attempts[i]
            dt_b, s_b = attempts[i + 1]
            gap_days  = (dt_b - dt_a).total_seconds() / 86400.0
            for window_key, (lo, hi) in _RETENTION_WINDOWS.items():
                if lo <= gap_days <= hi:
                    buckets[window_key].append(max(0.0, min(1.0, s_b)))

    return {
        f"retention_{k}": (round(sum(v) / len(v), 3) if v else None)
        for k, v in buckets.items()
    }
