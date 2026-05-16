"""Moteur adaptatif — constantes pédagogiques partagées.

Sans import projet : zéro risque de circular dependency.
database.py et ai_service.py importent depuis ici.
"""

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

# ── Biais mastery sur la sélection des types de questions ─────────────────────
# Fragile  → compréhension et reformulation avant tout.
# Maîtrisé → challenge et application en situation complexe.
_MASTERY_BIAS: dict[str, list[str]] = {
    "Fragile":  ["reformulation", "consequence", "cas_pratique"],
    "Maîtrisé": ["question_piege", "cas_pratique", "consequence"],
}
