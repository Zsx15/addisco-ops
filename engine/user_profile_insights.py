"""
Profil pédagogique enrichi V1 — TASK-049.
Fonction pure : aucun accès DB, aucun appel API, aucun ML.
Input  : dictionnaire de données pré-agrégées.
Output : insights pédagogiques explicables avec niveau de confiance.
"""

_PEDAGOGY_FR: dict[str, str] = {
    "logical":    "Analytique",
    "procedural": "Procédural",
    "narrative":  "Narratif",
    "analogy":    "Analogique",
}

_ERROR_LABELS_FR: dict[str, str] = {
    "oubli_etape":       "Oubli d'étape",
    "confusion_notion":  "Confusion de notion",
    "reponse_vague":     "Réponse trop vague",
    "erreur_ordre":      "Erreur d'ordre",
    "erreur_exception":  "Erreur d'exception",
    "mauvaise_priorite": "Mauvaise priorité",
    "hors_sujet":        "Réponse hors sujet",
}

_RECOMMENDATIONS_BY_STYLE: dict[str, list[str]] = {
    "logical": [
        "Les questions directes et les analyses structurées correspondent à votre tendance observée.",
        "Pratiquez des exercices d'argumentation pour renforcer la rigueur logique.",
    ],
    "procedural": [
        "Les cas pratiques étape par étape semblent adaptés à votre profil.",
        "Pratiquez des questions de conséquence pour consolider les enchaînements.",
    ],
    "narrative": [
        "Les reformulations et synthèses semblent correspondre à votre profil.",
        "Expliquez les notions à voix haute pour renforcer la mémorisation narrative.",
    ],
    "analogy": [
        "Les questions vrai/faux et pièges semblent correspondre à votre tendance.",
        "Reliez les nouvelles notions à des situations concrètes déjà maîtrisées.",
    ],
}

_RECOMMENDATIONS_BY_ERROR: dict[str, str] = {
    "oubli_etape":       "Pratiquez les procédures pas à pas pour réduire les oublis d'étapes.",
    "confusion_notion":  "Comparez activement les notions proches pour réduire les confusions observées.",
    "reponse_vague":     "Formulez des réponses précises en utilisant les termes du référentiel.",
    "erreur_ordre":      "Reconstruisez mentalement l'ordre des étapes avant de répondre.",
    "mauvaise_priorite": "Entraînez-vous à hiérarchiser les critères dans les cas pratiques.",
    "hors_sujet":        "Relisez la question pour cibler la notion précise demandée.",
}


def _compute_confidence(total_attempts: int) -> tuple[str, str]:
    if total_attempts < 10:
        return "low", "Faible (moins de 10 tentatives — insights à titre indicatif)"
    if total_attempts < 50:
        return "medium", "Modérée (10 à 50 tentatives)"
    return "high", "Élevée (plus de 50 tentatives)"


def _compute_pedagogical_signal(diff: float) -> tuple[str, str]:
    """Signal pédagogique basé sur l'écart entre le mode dominant et la moyenne globale."""
    if diff >= 0.15:
        return "strong", "Fort (écart marqué entre le mode dominant et la moyenne)"
    if diff >= 0.08:
        return "moderate", "Modéré (écart visible mais limité)"
    return "weak", "Faible (écart peu marqué — profil à confirmer avec plus de données)"


def compute_profile_insights(data: dict) -> dict:
    """
    Calcule les insights pédagogiques enrichis V1 depuis des données pré-agrégées.
    Fonction pure — aucun effet de bord.

    Clés attendues dans data :
      total_attempts      (int)
      avg_score           (float, 0-1)
      preferred_pedagogy  (str | None)
      logical_score       (float)
      procedural_score    (float)
      narrative_score     (float)
      analogy_score       (float)
      fragile_topics      (list[str])
      momentum            (float, [-1,1])
      consistency_score   (float, [0,1])
      error_type_counts   (dict[str, int])
      avg_response_time   (float | None, secondes)
    """
    total        = int(data.get("total_attempts") or 0)
    avg_score    = float(data.get("avg_score") or 0.0)
    pref         = data.get("preferred_pedagogy") or None
    fragile      = list(data.get("fragile_topics") or [])
    momentum     = float(data.get("momentum") or 0.0)
    consistency  = float(data.get("consistency_score") or 0.0)
    err_counts   = {k: v for k, v in (data.get("error_type_counts") or {}).items()
                    if k and k not in ("", "correct")}
    avg_rt       = data.get("avg_response_time")

    confidence, confidence_label = _compute_confidence(total)

    strengths:       list[str] = []
    weaknesses:      list[str] = []
    recommendations: list[str] = []
    signals:         dict      = {"total_attempts": total}

    if total == 0:
        return {
            "dominant_style":           None,
            "dominant_style_key":       None,
            "dominant_style_label":     None,
            "strengths":                [],
            "weaknesses":               [],
            "recommendations":          [
                "Effectuez des tentatives pour générer un profil pédagogique."
            ],
            "confidence":               "low",
            "confidence_label":         "Faible (aucune donnée disponible)",
            "signals_used":             signals,
            "pedagogical_signal":       None,
            "pedagogical_signal_label": None,
        }

    # ── Forces ───────────────────────────────────────────────────────────────
    if avg_score >= 0.75:
        strengths.append(
            f"Score global satisfaisant ({round(avg_score * 100)} %) — "
            "tendance observée à la bonne rétention des notions."
        )
        signals["avg_score"] = avg_score

    if pref:
        pref_score = float(data.get(f"{pref}_score") or 0.0)
        pref_label = _PEDAGOGY_FR.get(pref, pref)
        if pref_score >= 0.70:
            strengths.append(
                f"Meilleur taux de réussite sur le mode {pref_label} "
                f"({round(pref_score * 100)} %) — "
                "probable style d'apprentissage dominant (à confirmer)."
            )
            signals["preferred_pedagogy_score"] = pref_score

    if momentum > 0.05:
        strengths.append(
            f"Progression récente détectée (momentum +{round(momentum * 100)} % sur 7 jours) — "
            "signal favorable à confirmer avec la prochaine session."
        )
        signals["momentum"] = momentum

    if consistency >= 0.4:
        strengths.append(
            f"Régularité des sessions satisfaisante ({round(consistency * 100)} % des jours sur 30j) — "
            "tendance observée à une pratique régulière."
        )
        signals["consistency_score"] = consistency

    # ── Fragilités ────────────────────────────────────────────────────────────
    if fragile:
        shown = fragile[:3]
        suffix = " (et autres)" if len(fragile) > 3 else ""
        weaknesses.append(
            f"Notions à consolider : {', '.join(shown)}{suffix} — "
            "score moyen < 60 % sur ces sujets."
        )
        signals["fragile_topics_count"] = len(fragile)

    dominant_err = max(err_counts, key=err_counts.get) if err_counts else None
    if dominant_err:
        err_label = _ERROR_LABELS_FR.get(dominant_err, dominant_err)
        err_count = err_counts[dominant_err]
        weaknesses.append(
            f"Erreur fréquente observée : \"{err_label}\" ({err_count} occurrence{'s' if err_count > 1 else ''}) — "
            "signal à surveiller sur la prochaine session."
        )
        signals["dominant_error"] = dominant_err

    if momentum < -0.05:
        weaknesses.append(
            f"Signal de baisse récente détecté (momentum {round(momentum * 100)} % sur 7 jours) — "
            "à confirmer avec plus de données."
        )
        signals["momentum"] = momentum

    if consistency < 0.2 and total >= 10:
        weaknesses.append(
            "Régularité faible observée — "
            "des sessions plus fréquentes pourraient améliorer la rétention."
        )

    if avg_rt is not None and avg_rt > 90 and avg_score < 0.6:
        weaknesses.append(
            f"Temps de réponse moyen élevé ({round(avg_rt)} s) combiné à un score bas — "
            "signal de surcharge possible sur les questions complexes (à confirmer)."
        )
        signals["avg_response_time"] = avg_rt

    # ── Recommandations ───────────────────────────────────────────────────────
    if pref and pref in _RECOMMENDATIONS_BY_STYLE:
        recommendations.extend(_RECOMMENDATIONS_BY_STYLE[pref])

    if fragile:
        recommendations.append(
            "Ciblez en priorité les notions fragiles lors des prochaines sessions."
        )

    if dominant_err and dominant_err in _RECOMMENDATIONS_BY_ERROR:
        recommendations.append(_RECOMMENDATIONS_BY_ERROR[dominant_err])

    if consistency < 0.2 and total >= 10:
        recommendations.append(
            "Des sessions courtes quotidiennes sont probablement plus efficaces "
            "que des sessions longues espacées."
        )

    if not recommendations:
        recommendations.append(
            "Continuez au rythme actuel — "
            "les données sont encore insuffisantes pour des recommandations précises."
        )

    # ── Label style + signal pédagogique ─────────────────────────────────────
    dominant_style_label = None
    pedagogical_signal = None
    pedagogical_signal_label = None
    if pref:
        pref_score = float(data.get(f"{pref}_score") or 0.0)
        label_fr   = _PEDAGOGY_FR.get(pref, pref)
        diff       = pref_score - avg_score
        if pref_score > 0:
            dominant_style_label = (
                f"Tendance {label_fr} "
                f"({round(pref_score * 100)} % vs {round(avg_score * 100)} % globalement)"
            )
            pedagogical_signal, pedagogical_signal_label = _compute_pedagogical_signal(diff)

    return {
        "dominant_style":           _PEDAGOGY_FR.get(pref) if pref else None,
        "dominant_style_key":       pref,
        "dominant_style_label":     dominant_style_label,
        "strengths":                strengths,
        "weaknesses":               weaknesses,
        "recommendations":          recommendations,
        "confidence":               confidence,
        "confidence_label":         confidence_label,
        "signals_used":             signals,
        "pedagogical_signal":       pedagogical_signal,
        "pedagogical_signal_label": pedagogical_signal_label,
    }
