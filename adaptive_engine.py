"""Moteur adaptatif — constantes et logique pédagogique pure.

Sans import projet : zéro risque de circular dependency.
database.py et ai_service.py importent depuis ici.
"""
import random
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

# ── Répétition espacée ────────────────────────────────────────────────────────
# Intervalles de base par classe de maîtrise (en jours).
# Utilisés par _adaptive_interval() comme point de départ avant modulation par trend.
# Les valeurs brutes (1j/3j) sont dupliquées dans get_revision_suggestion() ORDER BY.
REVIEW_INTERVALS: dict[str, int] = {
    "Fragile":          1,
    "En consolidation": 3,
    "Maîtrisé":         7,
}

# ── Profil pédagogique utilisateur ────────────────────────────────────────────
# Mappage question_type → dimension du profil.
_PEDAGOGY_GROUPS: dict[str, list[str]] = {
    "logical":    ["question_directe"],
    "procedural": ["cas_pratique", "consequence"],
    "narrative":  ["reformulation"],
    "analogy":    ["vrai_faux", "question_piege"],
}

# ── Types de questions pédagogiques disponibles ───────────────────────────────
QUESTION_TYPES: list[str] = [
    "question_directe",
    "cas_pratique",
    "vrai_faux",
    "question_piege",
    "reformulation",
    "consequence",
]

# ── Intervalle adaptatif de révision ─────────────────────────────────────────

def _adaptive_interval(mastery_class: str, trend: str) -> int:
    """
    Retourne l'intervalle de révision (en jours) adapté à la tendance récente.

    Modulation par rapport à REVIEW_INTERVALS :
    - Fragile + Amélioration    → 2j  (progrès visible, délai légèrement allongé)
    - Fragile + autre           → 1j  (inchangé — situation critique)
    - En consolidation + Amélioration → 5j  (bonne trajectoire, espacer davantage)
    - En consolidation + Dégradation  → 2j  (surveillance renforcée)
    - En consolidation + autre        → 3j  (inchangé)
    - Maîtrisé                  → 7j  (inchangé — déjà maîtrisé)
    """
    base = REVIEW_INTERVALS.get(mastery_class, 3)
    if mastery_class == "Fragile":
        return 2 if trend == "Amélioration" else base
    if mastery_class == "En consolidation":
        if trend == "Amélioration":
            return 5
        if trend == "Dégradation":
            return 2
    return base


def classify_mastery(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrichit un DataFrame issu de get_chunk_stats() avec deux colonnes :
    - mastery_class : 'Fragile' | 'En consolidation' | 'Maîtrisé'
    - trend         : 'Amélioration' | 'Stable' | 'Dégradation' | 'N/A'

    Règles de classification :
    - Maîtrisé       : avg_score >= 0.8 ET attempts_count >= 3
    - Fragile        : avg_score < 0.6  (quel que soit le nombre de tentatives)
    - En consolidation : tout le reste

    Règles de tendance (uniquement si attempts_count >= 2) :
    - Amélioration : last_score > avg_score + 0.1
    - Dégradation  : last_score < avg_score - 0.1
    - Stable       : écart <= 0.1
    - N/A          : une seule tentative ou last_score absent
    """
    def _class(row):
        if row["avg_score"] < 0.6:
            return "Fragile"
        if row["avg_score"] >= 0.8 and row["attempts_count"] >= 3:
            return "Maîtrisé"
        return "En consolidation"

    def _trend(row):
        if row["attempts_count"] < 2 or pd.isna(row["last_score"]):
            return "N/A"
        delta = float(row["last_score"]) - float(row["avg_score"])
        if delta > 0.1:
            return "Amélioration"
        if delta < -0.1:
            return "Dégradation"
        return "Stable"

    def _next_review(row):
        try:
            last_dt = datetime.fromisoformat(str(row["last_attempt_date"]))
            days    = _adaptive_interval(row["mastery_class"], row["trend"])
            return last_dt + timedelta(days=days)
        except Exception:
            return None

    def _days_until(row):
        # pd.isna() requis : pandas 2.x peut convertir None → NaT (datetime64[us])
        # dans la colonne next_review ; `is None` ne capture pas NaT.
        nxt = row["next_review"]
        try:
            if nxt is None or pd.isna(nxt):
                return None
            return int((nxt.date() - datetime.now().date()).days)
        except Exception:
            return None

    def _review_status(row):
        d = row["days_until_review"]
        # Même guard : days_until_review peut être None ou NaN selon le chemin
        if d is None or pd.isna(d):
            return "—"
        if d < 0:
            return "En retard"
        if d == 0:
            return "Aujourd'hui"
        return f"Dans {d} jour{'s' if d > 1 else ''}"

    df = df.copy()
    df["mastery_class"]     = df.apply(_class, axis=1)
    df["trend"]             = df.apply(_trend, axis=1)
    df["next_review"]       = df.apply(_next_review, axis=1)
    df["days_until_review"] = df.apply(_days_until, axis=1)
    df["review_status"]     = df.apply(_review_status, axis=1)
    return df


# ── Biais mastery sur la sélection des types de questions ─────────────────────
# Fragile  → compréhension et reformulation avant tout.
# Maîtrisé → challenge et application en situation complexe.
_MASTERY_BIAS: dict[str, list[str]] = {
    "Fragile":  ["reformulation", "consequence", "cas_pratique"],
    "Maîtrisé": ["question_piege", "cas_pratique", "consequence"],
}


# ── Sélection et explication du type de question ──────────────────────────────

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

    profile_types = _PEDAGOGY_GROUPS.get(profile_pedagogy or "", []) if profile_pedagogy else []

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


# ── Métriques dynamiques du profil utilisateur ───────────────────────────────


def compute_momentum(rows: list[tuple[str, float]], window_days: int = 7) -> float:
    """
    Momentum = avg_score(derniers window_days jours) − avg_score(fenêtre précédente).
    Mesure l'accélération récente de la progression.
    Retourne 0.0 si l'un des deux intervalles est vide.
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
    Mesure la régularité de la progression session à session.
    Retourne 0.0 si moins de 2 jours d'activité.
    Borné à [−1.0, 1.0].
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


# ── Plan de session adaptatif ─────────────────────────────────────────────────

_OBJECTIVES: dict[tuple[str, str], str] = {
    ("Fragile",          "Dégradation"):  "Reprendre les fondamentaux — régression active détectée",
    ("Fragile",          "Amélioration"): "Ancrer les progrès récents — maintenir la dynamique fragile",
    ("Fragile",          "Stable"):       "Travail de fond — sortir de la zone fragile",
    ("Fragile",          "N/A"):          "Premier apprentissage structuré — 3 tentatives visées",
    ("En consolidation", "Dégradation"):  "Renforcement ciblé — risque de régression identifié",
    ("En consolidation", "Amélioration"): "Ancrage — progression à confirmer sur 2 séances",
    ("En consolidation", "Stable"):       "Révision de maintien — progression vers la maîtrise",
    ("En consolidation", "N/A"):          "Consolidation régulière — stabiliser les acquis",
    ("Maîtrisé",         "Dégradation"):  "Rappel urgent — érosion de maîtrise détectée",
    ("Maîtrisé",         "Amélioration"): "Rappel court — maîtrise solide, maintien long terme",
    ("Maîtrisé",         "Stable"):       "Rappel espacé — ancrage en mémoire long terme",
    ("Maîtrisé",         "N/A"):          "Vérification de maîtrise — rappel standard",
}

_DURATION_BY_MASTERY: dict[str, int] = {
    "Fragile":          8,
    "En consolidation": 6,
    "Maîtrisé":         3,
}


def _compute_priority_score(row: "pd.Series") -> float:
    """
    Score de priorité pour un chunk (usage interne à build_session_plan).

    Composantes (ordre décroissant) :
    1. Urgence révision  : +3.0 si retard (+ 0.1/j supplémentaire, cap 10j),
                           +2.5 si aujourd'hui, +1.5 si dans ≤ 2j
    2. Fragilité         : +2.0 Fragile, +1.0 En consolidation
    3. Tendance          : +1.0 Dégradation, −0.3 Amélioration
    4. Faible historique : +0.5 si attempts_count < 3
    """
    review_status  = str(row.get("review_status", "—"))
    mastery_class  = str(row.get("mastery_class", ""))
    trend          = str(row.get("trend", "N/A"))
    try:
        attempts_count = int(row.get("attempts_count", 0))
    except (TypeError, ValueError):
        attempts_count = 0

    days_raw = row.get("days_until_review")
    try:
        days_int: Optional[int] = None if (days_raw is None or pd.isna(days_raw)) else int(days_raw)
    except (TypeError, ValueError):
        days_int = None

    score: float = 0.0

    if review_status == "En retard":
        overdue = abs(days_int) if days_int is not None else 1
        score  += 3.0 + min(overdue, 10) * 0.1
    elif review_status == "Aujourd'hui":
        score  += 2.5
    elif days_int is not None and 0 < days_int <= 2:
        score  += 1.5

    if mastery_class == "Fragile":
        score += 2.0
    elif mastery_class == "En consolidation":
        score += 1.0

    if trend == "Dégradation":
        score += 1.0
    elif trend == "Amélioration":
        score -= 0.3

    if attempts_count < 3:
        score += 0.5

    return round(score, 3)


def build_session_plan(
    chunks_df: Optional["pd.DataFrame"],
    max_items: int = 5,
) -> list[dict]:
    """
    Construit le plan de session personnalisé depuis un DataFrame enrichi par classify_mastery().

    Colonnes requises dans chunks_df :
    chunk_id, mastery_class, trend, review_status, days_until_review,
    avg_score, attempts_count.

    Champs retournés par item :
    - chunk_id, section_label, document_title
    - mastery_class, trend, review_status, days_until_review, avg_score, attempts_count
    - priority_score    : score de tri interne (décroissant)
    - estimated_minutes : durée estimée en minutes (3–8)
    - objective         : texte de l'objectif pédagogique
    - question_bias     : types de questions recommandés pour cette section (biais mastery)
    """
    _required = {
        "chunk_id", "mastery_class", "trend", "review_status",
        "days_until_review", "avg_score", "attempts_count",
    }
    if chunks_df is None or chunks_df.empty:
        return []
    if not _required.issubset(chunks_df.columns):
        return []

    items: list[dict] = []
    for _, row in chunks_df.iterrows():
        mastery_class = str(row.get("mastery_class", ""))
        trend         = str(row.get("trend", "N/A"))
        review_status = str(row.get("review_status", "—"))

        objective = _OBJECTIVES.get((mastery_class, trend), "Révision adaptative")
        if review_status == "En retard":
            objective += " (révision en retard)"

        days_raw = row.get("days_until_review")
        try:
            days_out: Optional[int] = None if (days_raw is None or pd.isna(days_raw)) else int(days_raw)
        except (TypeError, ValueError):
            days_out = None

        items.append({
            "chunk_id":          int(row["chunk_id"]),
            "section_label":     str(row.get("section_label", "")),
            "document_title":    str(row.get("document_title", "")),
            "mastery_class":     mastery_class,
            "trend":             trend,
            "review_status":     review_status,
            "days_until_review": days_out,
            "avg_score":         float(row["avg_score"]),
            "attempts_count":    int(row["attempts_count"]),
            "priority_score":    _compute_priority_score(row),
            "estimated_minutes": _DURATION_BY_MASTERY.get(mastery_class, 5),
            "objective":         objective,
            "question_bias":     list(_MASTERY_BIAS.get(mastery_class, QUESTION_TYPES[:3])),
        })

    items.sort(key=lambda x: x["priority_score"], reverse=True)
    return items[:max_items]


def compute_consistency_score(rows: list[tuple[str, float]], window_days: int = 30) -> float:
    """
    Régularité = jours actifs dans les window_days derniers jours / window_days.
    Mesure la constance de la pratique.
    Retourne 0.0 si aucune session dans la fenêtre ou si window_days <= 0.
    Borné à [0.0, 1.0].
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


# ── Métriques de rétention pédagogique ───────────────────────────────────────

_RETENTION_WINDOWS: dict[str, tuple[float, float]] = {
    "j1":  (0.5,  2.5),   # 12h–60h  — révision lendemain
    "j7":  (4.0, 10.0),   # 4–10j    — révision hebdomadaire
    "j30": (21.0, 45.0),  # 21–45j   — révision mensuelle
}


def compute_retention_metrics(
    rows: list[tuple[int, str, float]],
) -> dict[str, Optional[float]]:
    """
    Mesure la rétention pédagogique sur 3 fenêtres temporelles.

    rows : liste de (chunk_id, created_at_iso, score).

    Méthode :
    - Groupe par chunk_id, trie chaque groupe par date.
    - Pour chaque paire consécutive (t_a, t_b), si l'écart tombe dans une
      fenêtre, le score de t_b (la « révision ») est collecté.
    - Valeur finale = moyenne des scores collectés par fenêtre.

    Retourne {"retention_j1": float|None, "retention_j7": float|None,
              "retention_j30": float|None}.
    None = aucune paire trouvée dans cette fenêtre.
    Toutes les valeurs numériques sont bornées à [0.0, 1.0].
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
