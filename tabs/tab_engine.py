"""Onglet Moteur IA — explication du pipeline pédagogique."""
import streamlit as st
from database import get_user_skill_mastery


def render() -> None:
    st.markdown(
        "<h3 style='margin:0 0 2px;color:#1e293b;font-size:18px'>Comment fonctionne ce moteur ?</h3>"
        "<p style='color:#64748b;font-size:13px;margin:0 0 10px'>"
        "Un pipeline en 7 étapes transforme vos documents métier en révision adaptative et personnalisée."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Parcours global ───────────────────────────────────────────────────
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 6px;text-transform:uppercase;"
        "letter-spacing:.05em'>Parcours global de l'apprenant</p>",
        unsafe_allow_html=True,
    )
    _journey = [
        ("📂", "Import",       "Le formateur charge un PDF ou TXT. Le système le découpe et le comprend."),
        ("🎯", "Session",      "L'apprenant répond à des questions générées sur le contenu réel du document."),
        ("✅", "Correction",   "L'IA identifie le type d'erreur et explique ce qui manque, ancré dans le document."),
        ("🧠", "Mémorisation", "Résultats enregistrés par notion : score, type d'erreur, date, section source."),
        ("🔄", "Révision",     "Le système rappelle au bon moment selon le niveau de maîtrise de chaque notion."),
        ("📈", "Maîtrise",     "Progression visible sur le tableau de bord — pour l'apprenant et le formateur."),
    ]
    _steps_html = ""
    for i, (ic, ti, de) in enumerate(_journey):
        arrow = (
            "<div style='display:flex;align-items:center;justify-content:center;"
            "color:#94a3b8;font-size:16px;padding:0 2px'>→</div>"
            if i < len(_journey) - 1 else ""
        )
        _steps_html += (
            f'<div style="flex:1;min-width:0;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:10px 10px;background:#fafbfc">'
            f'<div style="font-size:18px;margin-bottom:3px">{ic}</div>'
            f'<div style="font-size:11.5px;font-weight:700;color:#1e293b;margin-bottom:3px">{ti}</div>'
            f'<div style="font-size:11px;color:#64748b;line-height:1.4">{de}</div>'
            f'</div>'
            f'{arrow}'
        )
    st.markdown(
        f'<div style="display:flex;align-items:stretch;gap:4px;margin-bottom:14px;overflow-x:auto">'
        f'{_steps_html}</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Pipeline 7 étapes — grille 2 colonnes ────────────────────────────
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 6px;text-transform:uppercase;"
        "letter-spacing:.05em'>Pipeline pédagogique</p>",
        unsafe_allow_html=True,
    )
    _pipe_data = [
        ("📄", "Document",             "Importez un PDF ou TXT. Extraction, nettoyage et découpage en sections logiques."),
        ("🔍", "RAG",                  "Embeddings sémantiques par section. Retrieval par similarité cosinus lors de chaque session."),
        ("❓", "Question",             "Générée depuis la section pertinente, avec un type adapté à votre maîtrise actuelle."),
        ("✍️", "Réponse libre",        "Réponse en langage naturel. Temps de réponse mesuré, historique complet conservé."),
        ("✅", "Correction IA",        "Score, diagnostic d'erreur et explication ancrés dans le contenu source du document."),
        ("🧠", "Mémoire",              "Résultats enregistrés : score, notion, type d'erreur, section source, date."),
        ("🔄", "Révision prioritaire", "Prochaine révision calculée selon la maîtrise et l'algorithme de répétition espacée."),
    ]
    _pipe_html = "".join(
        f'<div style="border:1px solid #e2e8f0;border-radius:8px;padding:10px 13px;background:#fafbfc">'
        f'<div style="font-size:17px;margin-bottom:3px">{ic}</div>'
        f'<div style="font-size:12px;font-weight:600;color:#1e293b;margin-bottom:2px">{ti}</div>'
        f'<div style="font-size:11.5px;color:#64748b;line-height:1.4">{de}</div>'
        f'</div>'
        for ic, ti, de in _pipe_data
    )
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:14px">'
        f'{_pipe_html}</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── 6 types de questions — grille 3 colonnes ─────────────────────────
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 2px;text-transform:uppercase;"
        "letter-spacing:.05em'>6 types de questions adaptatives</p>"
        "<p style='font-size:12px;color:#64748b;margin:0 0 7px'>"
        "Le type est sélectionné automatiquement selon la maîtrise détectée pour chaque section.</p>",
        unsafe_allow_html=True,
    )
    _qt_data = [
        ("❶", "Question directe",  "Restitution directe d'une information clé.",                             "#f0f9ff", "#0369a1"),
        ("❷", "Reformulation",     "Expliquer avec ses mots — prioritaire pour les sections fragiles.",      "#fdf4ff", "#7e22ce"),
        ("❸", "Conséquence",       "Enchaînements logiques et conditions d'application.",                    "#fff7ed", "#c2410c"),
        ("❹", "Cas pratique",      "Application des règles en situation concrète.",                          "#f0fdf4", "#15803d"),
        ("❺", "Vrai / Faux",       "Distinguer vrai et faux — précision des connaissances.",                 "#f8fafc", "#475569"),
        ("❻", "Question piège",    "Formulations trompeuses — réservé aux sections maîtrisées.",             "#fef2f2", "#991b1b"),
    ]
    _qt_html = "".join(
        f'<div style="border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;background:{bg}">'
        f'<div style="font-size:11px;font-weight:700;color:{ac};text-transform:uppercase;'
        f'letter-spacing:.04em;margin-bottom:3px">{num} {lbl}</div>'
        f'<div style="font-size:11.5px;color:#475569;line-height:1.35">{dsc}</div>'
        f'</div>'
        for num, lbl, dsc, bg, ac in _qt_data
    )
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:14px">'
        f'{_qt_html}</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Répétition espacée + Adaptation cognitive — 2 colonnes ───────────
    _col_rep, _col_adp = st.columns(2)

    with _col_rep:
        st.markdown(
            "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 7px;"
            "text-transform:uppercase;letter-spacing:.05em'>Répétition espacée</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px">'
            '<div style="border:1px solid #fca5a5;border-radius:8px;padding:10px 8px;'
            'background:#fef2f2;text-align:center">'
            '<div style="font-size:18px">🔴</div>'
            '<div style="font-size:12px;font-weight:700;color:#991b1b;margin:3px 0">Fragile</div>'
            '<div style="font-size:11px;color:#b91c1c">Rappel · 1 j</div></div>'
            '<div style="border:1px solid #fde68a;border-radius:8px;padding:10px 8px;'
            'background:#fffbeb;text-align:center">'
            '<div style="font-size:18px">🟡</div>'
            '<div style="font-size:12px;font-weight:700;color:#92400e;margin:3px 0">Consolidation</div>'
            '<div style="font-size:11px;color:#b45309">Rappel · 3 j</div></div>'
            '<div style="border:1px solid #86efac;border-radius:8px;padding:10px 8px;'
            'background:#f0fdf4;text-align:center">'
            '<div style="font-size:18px">🟢</div>'
            '<div style="font-size:12px;font-weight:700;color:#166534;margin:3px 0">Maîtrisé</div>'
            '<div style="font-size:11px;color:#15803d">Rappel · 7 j</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with _col_adp:
        st.markdown(
            "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 7px;"
            "text-transform:uppercase;letter-spacing:.05em'>Adaptation cognitive</p>",
            unsafe_allow_html=True,
        )
        st.info(
            "🔴 **Fragile** → reformulation, conséquence  \n"
            "🟡 **En consolidation** → types variés  \n"
            "🟢 **Maîtrisé** → questions pièges, cas pratiques"
        )

    st.divider()

    # ── Graphe de compétences Bloom (données réelles) ────────────────────────
    _uid = st.session_state.get("user_id", "default")
    _skill_rows = get_user_skill_mastery(_uid)
    _mastery_map: dict[str, float] = {
        r["slug"]: float(r["mastery_score"] or 0) for r in _skill_rows
    }

    def _mastery_badge(slug: str) -> str:
        score = _mastery_map.get(slug)
        if score is None:
            return '<span style="font-size:10px;color:#94a3b8;margin-left:4px">—</span>'
        pct = round(score * 100)
        if score >= 0.80:
            color, bg = "#16a34a", "rgba(22,163,74,0.13)"
        elif score >= 0.60:
            color, bg = "#d97706", "rgba(217,119,6,0.13)"
        else:
            color, bg = "#dc2626", "rgba(220,38,38,0.13)"
        return (
            f'<span style="font-size:10px;font-weight:700;color:{color};'
            f'background:{bg};border-radius:3px;padding:1px 5px;margin-left:5px">'
            f'{pct}%</span>'
        )

    _BLOOM_LEVELS = [
        {
            "label": "Niveau 4 — Expertise", "cols": "1fr 1fr",
            "ct": "#be123c", "bg": "#fee2e2", "bd": "#fca5a5",
            "arrow": "↑ &nbsp; ↑",
            "skills": [
                ("prise_decision", "Prise de décision", "Choisir l'action adaptée face à une situation non standard"),
                ("evaluation_critique", "Évaluation critique", "Juger la pertinence d'une procédure dans un contexte donné"),
            ],
        },
        {
            "label": "Niveau 3 — Maîtrise", "cols": "1fr 1fr",
            "ct": "#7e22ce", "bg": "#ede9fe", "bd": "#c4b5fd",
            "arrow": "↑ &nbsp; ↑ &nbsp; ↑",
            "skills": [
                ("conformite_reglementaire", "Conformité réglementaire", "Appliquer les règles dans tous les cas, y compris les exceptions"),
                ("resolution_problemes", "Résolution de problèmes", "Trouver une issue face à un incident ou une situation imprévue"),
            ],
        },
        {
            "label": "Niveau 2 — Application", "cols": "1fr 1fr 1fr",
            "ct": "#c2410c", "bg": "#ffedd5", "bd": "#fdba74",
            "arrow": "↑",
            "skills": [
                ("application_regles", "Application des règles", "Mettre en œuvre la procédure dans une situation standard"),
                ("analyse_causale", "Analyse causale", "Identifier les causes et les enchaînements d'une situation"),
                ("synthese_reformulation", "Synthèse / Reformulation", "Restituer un concept avec ses propres mots"),
            ],
        },
        {
            "label": "Niveau 1 — Compréhension", "cols": "1fr",
            "ct": "#0f766e", "bg": "#ccfbf1", "bd": "#5eead4",
            "arrow": "↑ &nbsp; ↑",
            "skills": [
                ("comprehension_procedure", "Compréhension de la procédure", "Expliquer le sens et la logique d'une règle ou d'une étape"),
            ],
        },
        {
            "label": "Niveau 0 — Fondations", "cols": "1fr 1fr",
            "ct": "#1d4ed8", "bg": "#dbeafe", "bd": "#93c5fd",
            "arrow": None,
            "skills": [
                ("memorisation_faits", "Mémorisation des faits", "Retenir les informations clés d'un document de procédure"),
                ("identification_concepts", "Identification des concepts", "Reconnaître et nommer les notions essentielles d'un domaine"),
            ],
        },
    ]

    _bloom_html = ""
    for _lvl in _BLOOM_LEVELS:
        _ct, _bg, _bd, _cols = _lvl["ct"], _lvl["bg"], _lvl["bd"], _lvl["cols"]
        _cards = "".join(
            f'<div style="border:1px solid {_bd};border-left:4px solid {_ct};'
            f'border-radius:8px;padding:8px 10px;background:{_bg}">'
            f'<div style="font-size:11.5px;font-weight:600;color:{_ct};margin-bottom:3px">'
            f'{_lbl}{_mastery_badge(_slug)}</div>'
            f'<div style="font-size:11px;color:#64748b;line-height:1.35">{_desc}</div>'
            f'</div>'
            for _slug, _lbl, _desc in _lvl["skills"]
        )
        _bloom_html += (
            f'<div style="margin-bottom:6px">'
            f'<div style="font-size:10.5px;font-weight:700;color:{_ct};text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:5px;padding:3px 8px;background:{_bg};'
            f'border:1px solid {_bd};border-radius:4px;display:inline-block">{_lvl["label"]}</div>'
            f'<div style="display:grid;grid-template-columns:{_cols};gap:7px">{_cards}</div>'
            f'</div>'
        )
        if _lvl["arrow"]:
            _bloom_html += (
                f'<div style="text-align:center;color:#94a3b8;font-size:14px;margin:3px 0">'
                f'{_lvl["arrow"]}</div>'
            )

    _bloom_footer = (
        '<div style="border:1px solid #d1fae5;border-radius:8px;padding:8px 12px;'
        'background:#f0fdf4;font-size:11px;color:#166534">'
        '📊 <b>Données en temps réel.</b> Les scores reflètent vos sessions de travail.</div>'
    ) if _mastery_map else (
        '<div style="border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;'
        'background:#f8fafc;font-size:11px;color:#64748b">'
        '⏳ <b>En attente de données.</b> Les badges de maîtrise apparaissent '
        'dès la première session.</div>'
    )

    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 4px;"
        "text-transform:uppercase;letter-spacing:.05em'>Graphe de compétences — Taxonomie de Bloom</p>"
        "<p style='font-size:12px;color:#64748b;margin:0 0 12px'>"
        "10 compétences pédagogiques organisées en 5 niveaux de maîtrise progressive. "
        "Chaque niveau nécessite que les niveaux inférieurs soient acquis.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(_bloom_html + _bloom_footer, unsafe_allow_html=True)
