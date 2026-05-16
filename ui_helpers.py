"""
Fonctions utilitaires UI — rendu HTML, analyse pédagogique, rapport, explainability.
Aucune dépendance Streamlit : importable et testable indépendamment.
"""
import hmac
from datetime import datetime
from typing import Optional

import pandas as pd

_ERROR_LABELS: dict[str, str] = {
    "oubli_etape":     "Oubli d'étape",
    "confusion_notion": "Confusion de notion",
    "reponse_vague":   "Réponse vague",
    "erreur_ordre":    "Erreur d'ordre",
    "hors_sujet":      "Hors sujet",
    "correct":         "Correct",
}


def _truncate_label(text: str, max_len: int = 25) -> str:
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


def _kpi_card(icon: str, label: str, value: str, accent: str = "#0f172a") -> str:
    return (
        '<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;'
        'padding:20px 14px;text-align:center;'
        'box-shadow:0 1px 3px rgba(15,23,42,.08),0 1px 2px rgba(15,23,42,.04);">'
        f'<div style="font-size:22px;line-height:1;margin-bottom:10px">{icon}</div>'
        f'<div style="font-size:30px;font-weight:800;color:{accent};line-height:1;'
        f'margin-bottom:8px;letter-spacing:-0.02em">{value}</div>'
        f'<div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;'
        f'letter-spacing:.08em">{label}</div>'
        '</div>'
    )


def _mastery_state(row) -> tuple[str, str, str]:
    mc     = row.get("mastery_class", "")
    trend  = row.get("trend", "N/A")
    days   = row.get("days_until_review")
    overdue = isinstance(days, (int, float)) and days < 0

    if mc == "Maîtrisé":
        if overdue:
            return ("⚠️", "Oubli possible", "#9333ea")
        if trend == "Dégradation":
            return ("📉", "Maîtrise instable", "#d97706")
        return ("✅", "Maîtrisé", "#16a34a")

    if mc == "En consolidation":
        if trend == "Amélioration":
            return ("📈", "Forte progression", "#0891b2")
        if trend == "Dégradation":
            return ("📉", "Consolidation instable", "#d97706")
        if overdue:
            return ("⏰", "Révision en attente", "#7c3aed")
        return ("🔄", "Consolidation active", "#d97706")

    # Fragile
    if trend == "Amélioration":
        return ("📈", "En progression", "#0891b2")
    if trend == "Dégradation":
        return ("📉", "Régression active", "#dc2626")
    return ("⚡", "Fragilité confirmée", "#dc2626")


def _build_recommendations(
    df_chunks: pd.DataFrame, df_errors: pd.DataFrame
) -> list[tuple[str, str]]:
    recs: list[tuple[str, str]] = []
    if df_chunks.empty:
        return recs

    overdue = df_chunks[df_chunks["review_status"] == "En retard"]
    if len(overdue) == 1:
        recs.append(("urgent", f"Section \"{overdue.iloc[0]['section_label']}\" doit être revue aujourd'hui"))
    elif len(overdue) > 1:
        recs.append(("urgent", f"{len(overdue)} sections en retard de révision — priorité immédiate"))

    near = df_chunks[
        (df_chunks["avg_score"] >= 0.68) &
        (df_chunks["mastery_class"] == "En consolidation") &
        (df_chunks["trend"] == "Amélioration")
    ]
    for _, r in near.iterrows():
        recs.append(("success", f"\"{r['section_label']}\" proche de la maîtrise — {round(float(r['avg_score']) * 100)} %"))

    for _, r in df_chunks[df_chunks["trend"] == "Dégradation"].head(2).iterrows():
        recs.append(("warning", f"Régression détectée sur \"{r['section_label']}\" — révision recommandée"))

    if not df_errors.empty and int(df_errors.iloc[0]["count"]) >= 3:
        _te = df_errors.iloc[0]
        recs.append((
            "info",
            f"{int(_te['count'])} erreurs \"{_ERROR_LABELS.get(_te['error_type'], _te['error_type'])}\" — notion sensible identifiée",
        ))

    fragile_err = df_chunks[
        (df_chunks["mastery_class"] == "Fragile") &
        df_chunks["dominant_error_type"].notna() &
        (df_chunks["dominant_error_type"] != "")
    ]
    for _, r in fragile_err.head(1).iterrows():
        recs.append(("warning", f"\"{r['section_label']}\" : erreur répétée \"{_ERROR_LABELS.get(r['dominant_error_type'], r['dominant_error_type'])}\""))

    return recs[:5]


# ── Phase 9.5 — Decision Explainability Layer ─────────────────────────────────

_PROFILE_LABELS_FR: dict[str, tuple[str, str]] = {
    "logical":    ("Analytique",  "questions directes"),
    "procedural": ("Procédural",  "cas pratiques et conséquences"),
    "narrative":  ("Narratif",    "reformulations"),
    "analogy":    ("Analogique",  "vrai/faux et questions pièges"),
}


def explain_question_decision(
    question_type: str,
    mastery_class: Optional[str],
    trend: str,
    review_status: str,
    dominant_error: Optional[str],
    profile_pedagogy: Optional[str],
) -> list[tuple[str, str]]:
    """
    Produit une liste de signaux cognitifs expliquant la sélection de la question.
    Retourne des tuples (icône, texte) — aucune dépendance Streamlit.
    """
    signals: list[tuple[str, str]] = []

    _bias_map: dict[str, tuple[str, str]] = {
        "Fragile":          ("⚡", "Section fragile — reformulation et conséquence priorisées par le moteur"),
        "En consolidation": ("🔄", "Section en progression — types variés pour ancrer les acquis"),
        "Maîtrisé":         ("✅", "Section maîtrisée — questions pièges et cas pratiques pour challenger"),
    }
    if mastery_class and mastery_class in _bias_map:
        signals.append(_bias_map[mastery_class])

    if trend == "Amélioration":
        signals.append(("📈", "Progression récente détectée — consolidation des acquis en cours"))
    elif trend == "Dégradation":
        signals.append(("📉", "Régression récente — renforcement pédagogique actif"))

    if review_status == "En retard":
        signals.append(("⏰", "Révision en retard — rappel prioritaire déclenché par l'algorithme"))
    elif review_status == "Aujourd'hui":
        signals.append(("📅", "Révision prévue aujourd'hui selon l'intervalle calculé"))

    if dominant_error and dominant_error not in ("", "correct"):
        label = _ERROR_LABELS.get(dominant_error, dominant_error)
        signals.append(("🔍", f"Erreur récurrente identifiée : {label}"))

    if profile_pedagogy and profile_pedagogy in _PROFILE_LABELS_FR:
        prf_label = _PROFILE_LABELS_FR[profile_pedagogy][0]
        signals.append(("🎓", f"Profil {prf_label.lower()} détecté — type de question favorisé en conséquence"))

    return signals


def explain_interval_decision(mastery_class: str, trend: str) -> str:
    """
    Retourne une phrase expliquant l'intervalle de révision calculé par le moteur.
    Miroir narratif de _adaptive_interval() dans database.py — aucun import backend.
    """
    _special: dict[tuple[str, str], tuple[int, str]] = {
        ("Fragile",          "Amélioration"): (2, "section fragile en progression — délai légèrement allongé"),
        ("En consolidation", "Amélioration"): (5, "bonne trajectoire — espacement augmenté"),
        ("En consolidation", "Dégradation"):  (2, "consolidation dégradée — surveillance renforcée"),
    }
    _default: dict[str, tuple[int, str]] = {
        "Fragile":          (1, "rappel immédiat prioritaire"),
        "En consolidation": (3, "consolidation stable — intervalle standard"),
        "Maîtrisé":         (7, "section maîtrisée — espacement maximal"),
    }
    key = (mastery_class, trend)
    if key in _special:
        days, reason = _special[key]
        return f"Intervalle {days}j : {reason}"
    if mastery_class in _default:
        days, reason = _default[mastery_class]
        return f"Intervalle {days}j : {reason}"
    return ""


def explain_priority_decision(row: dict) -> list[str]:
    """
    Produit la liste de raisons algorithmiques justifiant la priorité de révision d'un chunk.
    row doit contenir : avg_score, mastery_class, review_status, trend,
                        dominant_error_type, attempts_count.
    Fonctionne avec dict ou pandas.Series (les deux ont .get()).
    """
    reasons: list[str] = []

    avg_score     = float(row.get("avg_score")           or 0.0)
    mastery_class = str(row.get("mastery_class")         or "")
    review_status = str(row.get("review_status")         or "—")
    trend         = str(row.get("trend")                 or "N/A")
    dominant_err  = str(row.get("dominant_error_type")   or "")
    attempts      = int(row.get("attempts_count")        or 0)
    pct           = round(avg_score * 100)

    if mastery_class == "Fragile":
        reasons.append(f"Score moyen : {pct} % — seuil de fragilité < 60 %")
    elif mastery_class == "En consolidation":
        reasons.append(f"Score moyen : {pct} % — section en cours de consolidation")

    if review_status == "En retard":
        reasons.append("Révision en retard selon l'intervalle calculé")
    elif review_status == "Aujourd'hui":
        reasons.append("Révision prévue aujourd'hui")

    if trend == "Dégradation":
        reasons.append("Régression récente détectée")
    elif trend == "Amélioration" and mastery_class == "Fragile":
        reasons.append("En progression — consolidation à encourager")

    if dominant_err and dominant_err not in ("", "correct"):
        label = _ERROR_LABELS.get(dominant_err, dominant_err)
        reasons.append(f"Erreur répétée : {label}")

    if attempts < 3:
        reasons.append(f"Peu de tentatives enregistrées ({attempts})")

    return reasons


def explain_profile_detection(profile: Optional[dict]) -> str:
    """
    Retourne une phrase expliquant pourquoi le profil pédagogique dominant a été détecté.
    Retourne une phrase d'attente si le profil est None ou insuffisant.
    """
    if not profile:
        return "Profil non encore établi — effectuez davantage de tentatives."

    pref = profile.get("preferred_pedagogy")
    if not pref or pref not in _PROFILE_LABELS_FR:
        return "Données insuffisantes pour établir un profil dominant."

    label, types_fr = _PROFILE_LABELS_FR[pref]
    score_key = f"{pref}_score"
    score     = float(profile.get(score_key) or 0.0)
    avg       = float(profile.get("average_score") or 0.0)
    score_pct = round(score * 100)
    avg_pct   = round(avg * 100)

    if score_pct > 0 and avg_pct > 0:
        return (
            f"Profil {label} dominant : meilleur taux de réussite sur les {types_fr} "
            f"({score_pct} % vs {avg_pct} % de moyenne globale)."
        )
    if score_pct > 0:
        return f"Profil {label} dominant : meilleur taux de réussite sur les {types_fr} ({score_pct} %)."
    return f"Profil {label} dominant détecté."


# ── Rapport texte brut ────────────────────────────────────────────────────────

def _build_report(df_all: pd.DataFrame, df_topics: pd.DataFrame, df_chunks: pd.DataFrame) -> str:
    w     = 60
    lines: list[str] = []

    def _sep(c: str = "=") -> None:   lines.append(c * w)
    def _h(t: str) -> None:           lines.extend([t, "-" * len(t)])
    def _blank() -> None:             lines.append("")

    _sep()
    lines.append("RAPPORT DE PROGRESSION — IA REVISION METIER")
    lines.append(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}")
    _sep()
    _blank()

    _h("SYNTHESE GLOBALE")
    scores = df_all["score"].dropna()
    lines.append(f"  Tentatives totales  : {len(df_all)}")
    lines.append(
        f"  Score moyen global  : {round(scores.mean() * 100)} %"
        if len(scores) else "  Score moyen global  : —"
    )
    if not df_topics.empty:
        lines.append(f"  Meilleure notion    : {df_topics.iloc[-1]['topic']}")
        lines.append(f"  Notion a renforcer  : {df_topics.iloc[0]['topic']}")
    _blank()

    if not df_chunks.empty:
        _h("MAITRISE PAR SECTION")
        _TAG = {
            "Fragile":          "[FRAGILE]         ",
            "En consolidation": "[EN CONSOLIDATION]",
            "Maitrise":         "[MAITRISE]        ",
            "Maîtrisé":         "[MAITRISE]        ",
        }
        for _, r in df_chunks.iterrows():
            tag   = _TAG.get(r["mastery_class"], f"[{r['mastery_class']}]")
            pct   = round(float(r["avg_score"]) * 100)
            n     = int(r["attempts_count"])
            rv_st = r.get("review_status", "—")
            lines.append(f"  {tag}  {_truncate_label(r['section_label'], 30)}  —  {pct} %  ·  {n} tent.  ·  {rv_st}")
        _blank()

        _h("PROCHAINES REVISIONS PRIORITAIRES")
        for _, r in df_chunks[df_chunks["mastery_class"] == "Fragile"].sort_values("avg_score").iterrows():
            rv_st = r.get("review_status", "—")
            mk    = "  ! " if rv_st == "En retard" else "    "
            lines.append(f"{mk}{r['section_label']}  [{rv_st}]  (Fragile)")
        for _, r in df_chunks[df_chunks["mastery_class"] == "En consolidation"].sort_values("avg_score").iterrows():
            rv_st = r.get("review_status", "—")
            mk    = "  ! " if rv_st == "En retard" else "    "
            lines.append(f"{mk}{r['section_label']}  [{rv_st}]  (En consolidation)")
        for _, r in df_chunks[df_chunks["mastery_class"] == "Maîtrisé"].iterrows():
            rv_st = r.get("review_status", "—")
            lines.append(f"    {r['section_label']}  [{rv_st}]  (Maitrise)")
        _blank()

    _sep()
    lines.append("Rapport genere par IA Revision Metier")
    _sep()
    return "\n".join(lines)


# ── Validation des entrées utilisateur (TASK-035) ─────────────────────────────

_USER_ID_MAX_LEN  = 50
_DOC_TITLE_MAX_LEN = 200
_FILE_MAX_MB       = 20
_FILE_MAX_BYTES    = _FILE_MAX_MB * 1024 * 1024


def sanitize_user_id(raw: str) -> str:
    """Strip et tronque user_id ; retourne 'default' si vide après nettoyage."""
    cleaned = raw.strip()[:_USER_ID_MAX_LEN]
    return cleaned if cleaned else "default"


def validate_doc_title(title: str) -> Optional[str]:
    """Retourne un message d'erreur ou None si le titre est valide."""
    stripped = title.strip()
    if not stripped:
        return "Veuillez saisir un titre."
    if len(stripped) > _DOC_TITLE_MAX_LEN:
        return f"Le titre est trop long ({len(stripped)} caractères, maximum {_DOC_TITLE_MAX_LEN})."
    return None


def validate_file_size(size_bytes: int) -> Optional[str]:
    """Retourne un message d'erreur ou None si la taille est acceptable."""
    if size_bytes > _FILE_MAX_BYTES:
        mb = size_bytes // (1024 * 1024)
        return f"Fichier trop volumineux ({mb} Mo). Limite : {_FILE_MAX_MB} Mo."
    return None


def check_app_password(entered: str, expected: str) -> bool:
    """Vérifie le mot de passe d'application en temps constant (anti-timing attack)."""
    return hmac.compare_digest(entered, expected)
