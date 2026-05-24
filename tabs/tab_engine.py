"""Onglet Moteur IA — explication du pipeline pédagogique."""
import streamlit as st


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

    # ── Graphe de compétences Bloom (statique) ────────────────────────────
    st.markdown(
        "<p style='font-size:13px;font-weight:700;color:#1e293b;margin:0 0 4px;"
        "text-transform:uppercase;letter-spacing:.05em'>Graphe de compétences — Taxonomie de Bloom</p>"
        "<p style='font-size:12px;color:#64748b;margin:0 0 12px'>"
        "10 compétences pédagogiques organisées en 5 niveaux de maîtrise progressive. "
        "Chaque niveau nécessite que les niveaux inférieurs soient acquis.</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        # Niveau 4 — Expertise
        '<div style="margin-bottom:6px">'
        '<div style="font-size:10.5px;font-weight:700;color:#be123c;text-transform:uppercase;'
        'letter-spacing:.06em;margin-bottom:5px;padding:3px 8px;background:#fee2e2;'
        'border:1px solid #fca5a5;border-radius:4px;display:inline-block">Niveau 4 — Expertise</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:7px">'
        '<div style="border:1px solid #fca5a5;border-left:4px solid #be123c;border-radius:8px;padding:8px 10px;background:#fee2e2">'
        '<div style="font-size:11.5px;font-weight:600;color:#be123c;margin-bottom:3px">Prise de décision</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Choisir l\'action adaptée face à une situation non standard</div></div>'
        '<div style="border:1px solid #fca5a5;border-left:4px solid #be123c;border-radius:8px;padding:8px 10px;background:#fee2e2">'
        '<div style="font-size:11.5px;font-weight:600;color:#be123c;margin-bottom:3px">Évaluation critique</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Juger la pertinence d\'une procédure dans un contexte donné</div></div>'
        '</div></div>'
        # Flèche
        '<div style="text-align:center;color:#94a3b8;font-size:14px;margin:3px 0">↑ &nbsp; ↑</div>'
        # Niveau 3 — Maîtrise
        '<div style="margin-bottom:6px">'
        '<div style="font-size:10.5px;font-weight:700;color:#7e22ce;text-transform:uppercase;'
        'letter-spacing:.06em;margin-bottom:5px;padding:3px 8px;background:#ede9fe;'
        'border:1px solid #c4b5fd;border-radius:4px;display:inline-block">Niveau 3 — Maîtrise</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:7px">'
        '<div style="border:1px solid #c4b5fd;border-left:4px solid #7e22ce;border-radius:8px;padding:8px 10px;background:#ede9fe">'
        '<div style="font-size:11.5px;font-weight:600;color:#7e22ce;margin-bottom:3px">Conformité réglementaire</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Appliquer les règles dans tous les cas, y compris les exceptions</div></div>'
        '<div style="border:1px solid #c4b5fd;border-left:4px solid #7e22ce;border-radius:8px;padding:8px 10px;background:#ede9fe">'
        '<div style="font-size:11.5px;font-weight:600;color:#7e22ce;margin-bottom:3px">Résolution de problèmes</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Trouver une issue face à un incident ou une situation imprévue</div></div>'
        '</div></div>'
        # Flèche
        '<div style="text-align:center;color:#94a3b8;font-size:14px;margin:3px 0">↑ &nbsp; ↑ &nbsp; ↑</div>'
        # Niveau 2 — Application
        '<div style="margin-bottom:6px">'
        '<div style="font-size:10.5px;font-weight:700;color:#c2410c;text-transform:uppercase;'
        'letter-spacing:.06em;margin-bottom:5px;padding:3px 8px;background:#ffedd5;'
        'border:1px solid #fdba74;border-radius:4px;display:inline-block">Niveau 2 — Application</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px">'
        '<div style="border:1px solid #fdba74;border-left:4px solid #c2410c;border-radius:8px;padding:8px 10px;background:#ffedd5">'
        '<div style="font-size:11.5px;font-weight:600;color:#c2410c;margin-bottom:3px">Application des règles</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Mettre en œuvre la procédure dans une situation standard</div></div>'
        '<div style="border:1px solid #fdba74;border-left:4px solid #c2410c;border-radius:8px;padding:8px 10px;background:#ffedd5">'
        '<div style="font-size:11.5px;font-weight:600;color:#c2410c;margin-bottom:3px">Analyse causale</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Identifier les causes et les enchaînements d\'une situation</div></div>'
        '<div style="border:1px solid #fdba74;border-left:4px solid #c2410c;border-radius:8px;padding:8px 10px;background:#ffedd5">'
        '<div style="font-size:11.5px;font-weight:600;color:#c2410c;margin-bottom:3px">Synthèse / Reformulation</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Restituer un concept avec ses propres mots</div></div>'
        '</div></div>'
        # Flèche
        '<div style="text-align:center;color:#94a3b8;font-size:14px;margin:3px 0">↑</div>'
        # Niveau 1 — Compréhension
        '<div style="margin-bottom:6px">'
        '<div style="font-size:10.5px;font-weight:700;color:#0f766e;text-transform:uppercase;'
        'letter-spacing:.06em;margin-bottom:5px;padding:3px 8px;background:#ccfbf1;'
        'border:1px solid #5eead4;border-radius:4px;display:inline-block">Niveau 1 — Compréhension</div>'
        '<div style="display:grid;grid-template-columns:1fr;gap:7px">'
        '<div style="border:1px solid #5eead4;border-left:4px solid #0f766e;border-radius:8px;padding:8px 10px;background:#ccfbf1">'
        '<div style="font-size:11.5px;font-weight:600;color:#0f766e;margin-bottom:3px">Compréhension de la procédure</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Expliquer le sens et la logique d\'une règle ou d\'une étape</div></div>'
        '</div></div>'
        # Flèche
        '<div style="text-align:center;color:#94a3b8;font-size:14px;margin:3px 0">↑ &nbsp; ↑</div>'
        # Niveau 0 — Fondations
        '<div style="margin-bottom:10px">'
        '<div style="font-size:10.5px;font-weight:700;color:#1d4ed8;text-transform:uppercase;'
        'letter-spacing:.06em;margin-bottom:5px;padding:3px 8px;background:#dbeafe;'
        'border:1px solid #93c5fd;border-radius:4px;display:inline-block">Niveau 0 — Fondations</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:7px">'
        '<div style="border:1px solid #93c5fd;border-left:4px solid #1d4ed8;border-radius:8px;padding:8px 10px;background:#dbeafe">'
        '<div style="font-size:11.5px;font-weight:600;color:#1d4ed8;margin-bottom:3px">Mémorisation des faits</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Retenir les informations clés d\'un document de procédure</div></div>'
        '<div style="border:1px solid #93c5fd;border-left:4px solid #1d4ed8;border-radius:8px;padding:8px 10px;background:#dbeafe">'
        '<div style="font-size:11.5px;font-weight:600;color:#1d4ed8;margin-bottom:3px">Identification des concepts</div>'
        '<div style="font-size:11px;color:#64748b;line-height:1.35">Reconnaître et nommer les notions essentielles d\'un domaine</div></div>'
        '</div></div>'
        # Note
        '<div style="border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;'
        'background:#f8fafc;font-size:11px;color:#64748b">'
        '&#9881;&#65039; <b>Module fonctionnel — non connecté à l\'interface.</b> '
        'Choix délibéré : les métriques par compétence ne sont significatives qu\'à partir '
        'd\'un volume suffisant de sessions réelles (~500 tentatives). '
        'Le branchement est prévu dès que les données le permettent.</div>',
        unsafe_allow_html=True,
    )
