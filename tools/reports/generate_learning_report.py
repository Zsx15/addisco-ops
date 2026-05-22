#!/usr/bin/env python
"""
generate_learning_report.py — Rapports pédagogiques HTML V1 (TASK-062)

Génère un rapport pédagogique complet par utilisateur à partir des données en base.

Usage (depuis la racine du projet) :
    python tools/reports/generate_learning_report.py
    python tools/reports/generate_learning_report.py --user_id alice
    python tools/reports/generate_learning_report.py --user_id alice --output_dir reports/

Read-only strict : aucune écriture SQL, aucun appel API.
Sortie : reports/rapport_<user_id>_<YYYYMMDD>.html
"""
import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Imports projet ─────────────────────────────────────────────────────────────
from database import (
    init_db,
    get_attempts,
    get_score_evolution,
    get_chunk_stats,
    get_error_frequency,
    get_learning_profile,
    get_retention_metrics,
    get_next_session_plan,
)
from engine.error_pattern_memory import detect_persistent_error_patterns

# ── Constantes ─────────────────────────────────────────────────────────────────
_MASTERY_COLOR = {
    "Maîtrisé":      "#16a34a",
    "En consolidation": "#d97706",
    "Fragile":        "#dc2626",
}
_TREND_ICON = {"Amélioration": "↑", "Dégradation": "↓", "Stable": "→"}
_ERROR_LABELS = {
    "oubli_etape":       "Oubli d'étape",
    "confusion_notion":  "Confusion de notion",
    "reponse_vague":     "Réponse trop vague",
    "erreur_ordre":      "Erreur d'ordre",
    "hors_sujet":        "Hors sujet",
    "non_evaluable":     "Non évaluable",
    "mauvaise_priorite": "Mauvaise priorité",
}
_SEVERITY_COLOR = {
    "critique":        "#dc2626",
    "chronique":       "#ea580c",
    "récent":          "#d97706",
    "en_amelioration": "#16a34a",
    "stabilisé":       "#94a3b8",
}


# ── Collecte des données ───────────────────────────────────────────────────────

def _collect(user_id: str) -> dict:
    df_attempts  = get_attempts(user_id)
    df_scores    = get_score_evolution(limit=20, user_id=user_id)
    df_chunks    = get_chunk_stats(user_id)
    df_errors    = get_error_frequency(user_id)
    profile      = get_learning_profile(user_id)
    retention    = get_retention_metrics(user_id)
    session_plan = get_next_session_plan(user_id, max_items=5)
    error_patt   = detect_persistent_error_patterns(user_id)

    n_attempts  = len(df_attempts)
    avg_score   = float(df_attempts["score"].mean()) if n_attempts > 0 else None
    avg_time    = float(df_attempts["response_time_seconds"].dropna().mean()) if n_attempts > 0 else None

    # Période analysée
    if n_attempts > 0 and "created_at" in df_attempts.columns:
        dates = df_attempts["created_at"].dropna()
        period_start = str(dates.min())[:10] if not dates.empty else "—"
        period_end   = str(dates.max())[:10] if not dates.empty else "—"
    else:
        period_start = period_end = "—"

    # Sections par niveau de maîtrise
    mastered = consolidated = fragile = []
    if not df_chunks.empty and "avg_score" in df_chunks.columns:
        from adaptive_engine import classify_mastery
        enriched = classify_mastery(df_chunks)
        mastered      = enriched[enriched["mastery_class"] == "Maîtrisé"].to_dict("records")
        consolidated  = enriched[enriched["mastery_class"] == "En consolidation"].to_dict("records")
        fragile       = enriched[enriched["mastery_class"] == "Fragile"].to_dict("records")

    return {
        "user_id":      user_id,
        "n_attempts":   n_attempts,
        "avg_score":    avg_score,
        "avg_time":     avg_time,
        "period_start": period_start,
        "period_end":   period_end,
        "df_scores":    df_scores,
        "df_errors":    df_errors,
        "profile":      profile,
        "retention":    retention,
        "session_plan": session_plan,
        "error_patt":   error_patt,
        "mastered":     mastered,
        "consolidated": consolidated,
        "fragile":      fragile,
    }


# ── Helpers HTML ───────────────────────────────────────────────────────────────

def _pct(v: Optional[float]) -> str:
    return f"{v:.0%}" if v is not None else "—"


def _score_bar(v: Optional[float], width: int = 120) -> str:
    if v is None:
        return '<span style="color:#94a3b8">—</span>'
    filled = int(v * width)
    color  = "#16a34a" if v >= 0.75 else "#d97706" if v >= 0.50 else "#dc2626"
    return (
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<div style="width:{width}px;height:10px;background:#e2e8f0;border-radius:5px;overflow:hidden">'
        f'<div style="width:{filled}px;height:10px;background:{color};border-radius:5px"></div>'
        f'</div>'
        f'<span style="font-size:13px;color:{color};font-weight:600">{v:.0%}</span>'
        f'</div>'
    )


def _kpi_card(label: str, value: str, color: str = "#4f46e5", note: str = "") -> str:
    note_html = f'<div style="font-size:11px;color:#94a3b8;margin-top:2px">{note}</div>' if note else ""
    return (
        f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;'
        f'padding:20px 24px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)">'
        f'<div style="font-size:28px;font-weight:800;color:{color}">{value}</div>'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;'
        f'color:#64748b;margin-top:4px">{label}</div>'
        f'{note_html}'
        f'</div>'
    )


def _section_title(num: str, title: str) -> str:
    return (
        f'<div style="margin:32px 0 12px;border-left:4px solid #4f46e5;padding-left:12px">'
        f'<span style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;'
        f'color:#6366f1">{num}</span>'
        f'<h2 style="margin:2px 0 0;font-size:18px;color:#1e293b">{title}</h2>'
        f'</div>'
    )


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color}20;color:{color};border:1px solid {color}40;'
        f'border-radius:6px;padding:2px 8px;font-size:12px;font-weight:600">{text}</span>'
    )


def _table_row(*cells: str, header: bool = False) -> str:
    tag  = "th" if header else "td"
    bg   = "#f8fafc" if header else "#fff"
    rows = "".join(
        f'<{tag} style="padding:10px 14px;border-bottom:1px solid #f1f5f9;'
        f'font-size:13px;white-space:nowrap">{c}</{tag}>'
        for c in cells
    )
    return f'<tr style="background:{bg}">{rows}</tr>'


# ── Résumé exécutif ────────────────────────────────────────────────────────────

def _executive_summary(d: dict) -> str:
    avg = d["avg_score"]
    n   = d["n_attempts"]

    if n == 0:
        return "<p>Aucune tentative enregistrée pour cet utilisateur.</p>"

    if avg is None:
        level_text = "indéterminé"
        color      = "#94a3b8"
    elif avg >= 0.80:
        level_text = "excellent"
        color      = "#16a34a"
    elif avg >= 0.65:
        level_text = "en bonne progression"
        color      = "#0ea5e9"
    elif avg >= 0.50:
        level_text = "en consolidation"
        color      = "#d97706"
    else:
        level_text = "fragile — révision prioritaire"
        color      = "#dc2626"

    n_fragile = len(d["fragile"])
    n_master  = len(d["mastered"])

    fragile_note = ""
    if n_fragile > 0:
        fragile_note = (
            f" {n_fragile} section{'s' if n_fragile > 1 else ''} "
            f"reste{'nt' if n_fragile > 1 else ''} fragile{'s' if n_fragile > 1 else ''} "
            f"et nécessite{'nt' if n_fragile > 1 else ''} une attention prioritaire."
        )

    master_note = ""
    if n_master > 0:
        master_note = (
            f" {n_master} section{'s' if n_master > 1 else ''} "
            f"{'sont' if n_master > 1 else 'est'} maîtrisée{'s' if n_master > 1 else ''}."
        )

    return (
        f'<div style="background:{color}10;border-left:4px solid {color};'
        f'border-radius:0 8px 8px 0;padding:16px 20px;margin:16px 0">'
        f'<p style="margin:0;font-size:15px;line-height:1.6;color:#1e293b">'
        f'Avec <strong>{n} tentative{"s" if n > 1 else ""}</strong> enregistrées '
        f'du <strong>{d["period_start"]}</strong> au <strong>{d["period_end"]}</strong>, '
        f'le niveau global est <strong style="color:{color}">{level_text}</strong> '
        f'(score moyen&nbsp;: <strong>{_pct(avg)}</strong>).'
        f'{fragile_note}{master_note}'
        f'</p>'
        f'</div>'
    )


# ── Génération HTML ────────────────────────────────────────────────────────────

def _build_html(d: dict, generated_at: str) -> str:
    user_id = d["user_id"]

    # ── CSS ───────────────────────────────────────────────────────────────────
    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #f5f6fa;
        color: #1e293b;
        padding: 32px 16px;
    }
    .container { max-width: 900px; margin: 0 auto; }
    table { width: 100%; border-collapse: collapse; }
    @media print {
        body { background: #fff; padding: 16px; }
        .no-print { display: none; }
    }
    """

    # ── En-tête ───────────────────────────────────────────────────────────────
    header = f"""
    <div style="background:linear-gradient(135deg,#4f46e5,#6366f1);
                border-radius:16px;padding:32px 36px;color:#fff;margin-bottom:24px">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.15em;
                    opacity:.8;margin-bottom:8px">ADDISCO OPS · Rapport Pédagogique</div>
        <h1 style="font-size:26px;font-weight:800;margin-bottom:4px">{user_id}</h1>
        <div style="opacity:.85;font-size:14px">
            Période&nbsp;: {d['period_start']} → {d['period_end']}
            &nbsp;·&nbsp;
            Généré le {generated_at}
        </div>
    </div>
    """

    # ── Résumé exécutif ───────────────────────────────────────────────────────
    exec_summary = _section_title("01", "Résumé exécutif") + _executive_summary(d)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    ret    = d["retention"]
    r_j1   = _pct(ret.get("retention_j1"))
    r_j7   = _pct(ret.get("retention_j7"))
    avg_t  = f"{d['avg_time']:.0f}s" if d["avg_time"] else "—"

    kpis = f"""
    {_section_title("02", "Indicateurs clés")}
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
        {_kpi_card("Tentatives", str(d['n_attempts']))}
        {_kpi_card("Score moyen", _pct(d['avg_score']),
                   "#16a34a" if (d['avg_score'] or 0) >= 0.65 else "#d97706")}
        {_kpi_card("Rétention J+1", r_j1, "#0ea5e9", note=f"J+7 : {r_j7}")}
        {_kpi_card("Temps moyen", avg_t, "#6366f1")}
    </div>
    """

    # ── Maîtrise par section ──────────────────────────────────────────────────
    def _chunk_rows(items: list, cls: str, color: str) -> str:
        if not items:
            return ""
        rows = "".join(
            _table_row(
                r.get("section_label", f"Section {r.get('chunk_id','')}"),
                r.get("document_title", "—")[:35],
                _score_bar(r.get("avg_score")),
                _badge(cls, color),
                str(r.get("attempts_count", "—")),
            )
            for r in items[:15]
        )
        return rows

    mastery_table = f"""
    {_section_title("03", "Maîtrise par section")}
    <div style="background:#fff;border-radius:12px;overflow:hidden;
                box-shadow:0 1px 4px rgba(0,0,0,.06)">
        <table>
            {_table_row("Section", "Document", "Score", "Niveau", "Tentatives", header=True)}
            {_chunk_rows(d['fragile'],      'Fragile',           '#dc2626')}
            {_chunk_rows(d['consolidated'], 'En consolidation',  '#d97706')}
            {_chunk_rows(d['mastered'],     'Maîtrisé',          '#16a34a')}
        </table>
    </div>
    """ if (d["fragile"] or d["consolidated"] or d["mastered"]) else (
        _section_title("03", "Maîtrise par section")
        + '<p style="color:#94a3b8;font-size:14px">Pas encore de données de maîtrise.</p>'
    )

    # ── Profil d'apprentissage ────────────────────────────────────────────────
    profile = d["profile"]
    if profile:
        style_map = {
            "logical":    ("Analytique",   "#4f46e5"),
            "procedural": ("Procédural",   "#0ea5e9"),
            "narrative":  ("Narratif",     "#d97706"),
            "analogy":    ("Analogique",   "#6366f1"),
        }
        dominant = profile.get("preferred_pedagogy", "")
        profile_bars = "".join(
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:13px;margin-bottom:4px">'
            f'<span>{label} {"★" if key == dominant else ""}</span>'
            f'<span style="color:{color};font-weight:600">'
            f'{profile.get(key + "_score", 0.0):.0%}</span>'
            f'</div>'
            f'{_score_bar(profile.get(key + "_score", 0.0), width=200)}'
            f'</div>'
            for key, (label, color) in style_map.items()
        )
        momentum = profile.get("momentum", 0) or 0
        velocity = profile.get("learning_velocity", 0) or 0
        consist  = profile.get("consistency_score", 0) or 0
        profile_section = f"""
        {_section_title("04", "Profil d'apprentissage")}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
            <div style="background:#fff;border-radius:12px;padding:20px;
                        box-shadow:0 1px 4px rgba(0,0,0,.06)">
                <h3 style="font-size:14px;color:#64748b;margin-bottom:16px;
                            text-transform:uppercase;letter-spacing:.07em">Styles pédagogiques</h3>
                {profile_bars}
            </div>
            <div style="background:#fff;border-radius:12px;padding:20px;
                        box-shadow:0 1px 4px rgba(0,0,0,.06)">
                <h3 style="font-size:14px;color:#64748b;margin-bottom:16px;
                            text-transform:uppercase;letter-spacing:.07em">Dynamique</h3>
                <div style="margin-bottom:12px">
                    <div style="font-size:13px;margin-bottom:4px">Momentum (7 jours)</div>
                    {_score_bar(abs(momentum) / max(abs(momentum), 0.01) if momentum else 0)}
                    <div style="font-size:11px;color:#94a3b8">
                        {"↑ Accélération" if momentum > 0.01 else "↓ Décélération" if momentum < -0.01 else "→ Stable"}
                    </div>
                </div>
                <div style="margin-bottom:12px">
                    <div style="font-size:13px;margin-bottom:4px">Vitesse d'apprentissage</div>
                    {_score_bar(min(max((velocity + 1) / 2, 0), 1))}
                </div>
                <div>
                    <div style="font-size:13px;margin-bottom:4px">Régularité des sessions</div>
                    {_score_bar(consist)}
                </div>
            </div>
        </div>
        """
    else:
        profile_section = (
            _section_title("04", "Profil d'apprentissage")
            + '<p style="color:#94a3b8;font-size:14px">Profil non encore calculé.</p>'
        )

    # ── Patterns d'erreurs ────────────────────────────────────────────────────
    patt_data = d["error_patt"]
    patterns  = patt_data.get("patterns", [])
    if patterns:
        patt_rows = "".join(
            _table_row(
                _ERROR_LABELS.get(p["error_type"], p["error_type"]),
                str(p["count"]),
                _pct(p.get("avg_score")),
                _badge(
                    p["trend"],
                    _SEVERITY_COLOR.get(p["trend"], "#64748b"),
                ),
                f"{p.get('last_seen_days', '?')}j",
            )
            for p in patterns[:8]
        )
        patterns_section = f"""
        {_section_title("05", "Patterns d'erreurs actifs")}
        <div style="background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,0,0,.06)">
            <table>
                {_table_row("Type d'erreur", "Occurrences", "Score moyen", "Tendance", "Vu il y a", header=True)}
                {patt_rows}
            </table>
        </div>
        """
    else:
        df_errors = d["df_errors"]
        if not df_errors.empty:
            err_rows = "".join(
                _table_row(
                    _ERROR_LABELS.get(r["error_type"], r["error_type"]),
                    str(r["count"]),
                )
                for _, r in df_errors.iterrows()
            )
            patterns_section = f"""
            {_section_title("05", "Fréquence des erreurs")}
            <div style="background:#fff;border-radius:12px;overflow:hidden;
                        box-shadow:0 1px 4px rgba(0,0,0,.06)">
                <table>
                    {_table_row("Type d'erreur", "Occurrences", header=True)}
                    {err_rows}
                </table>
            </div>
            """
        else:
            patterns_section = (
                _section_title("05", "Patterns d'erreurs")
                + '<p style="color:#94a3b8;font-size:14px">Aucune erreur récurrente détectée.</p>'
            )

    # ── Recommandations ───────────────────────────────────────────────────────
    plan = d["session_plan"]
    if plan:
        reco_items = "".join(
            f'<div style="background:#fff;border-radius:10px;padding:16px 18px;'
            f'margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.05);'
            f'border-left:3px solid {_MASTERY_COLOR.get(p.get("mastery_class",""), "#4f46e5")}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<strong style="font-size:14px">{p.get("section_label","Section")[:60]}</strong>'
            f'<span style="font-size:12px;color:#94a3b8">~{p.get("estimated_minutes","?")} min</span>'
            f'</div>'
            f'<div style="font-size:12px;color:#64748b;margin-top:4px">'
            f'{p.get("document_title","")[:50]}</div>'
            f'<div style="font-size:13px;color:#475569;margin-top:8px">'
            f'{p.get("objective","")}</div>'
            f'</div>'
            for p in plan
        )
        recommendations = f"""
        {_section_title("06", "Recommandations — Plan de session")}
        {reco_items}
        """
    else:
        recommendations = (
            _section_title("06", "Recommandations — Plan de session")
            + '<p style="color:#94a3b8;font-size:14px">Pas encore de données suffisantes pour générer un plan.</p>'
        )

    # ── Sections problématiques ───────────────────────────────────────────────
    fragile = d["fragile"]
    if fragile:
        prob_rows = "".join(
            _table_row(
                r.get("section_label", f"Section {r.get('chunk_id','')}"),
                r.get("document_title", "—")[:40],
                _score_bar(r.get("avg_score")),
                _ERROR_LABELS.get(r.get("dominant_error_type", ""), r.get("dominant_error_type", "—")),
                str(r.get("attempts_count", "—")),
            )
            for r in sorted(fragile, key=lambda x: x.get("avg_score") or 1)[:10]
        )
        problematic_section = f"""
        {_section_title("07", "Sections prioritaires à réviser")}
        <div style="background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,0,0,.06)">
            <table>
                {_table_row("Section", "Document", "Score", "Erreur dominante", "Tentatives", header=True)}
                {prob_rows}
            </table>
        </div>
        """
    else:
        problematic_section = (
            _section_title("07", "Sections prioritaires à réviser")
            + '<p style="color:#16a34a;font-size:14px">Aucune section fragile détectée.</p>'
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    footer = f"""
    <div class="no-print" style="margin-top:40px;padding:20px;background:#fff;
                border-radius:12px;border:1px solid #e2e8f0;text-align:center;
                font-size:13px;color:#64748b">
        <strong>Exporter en PDF :</strong> Ctrl+P (ou ⌘+P) → Enregistrer en PDF
        &nbsp;·&nbsp;
        Généré par ADDISCO OPS · {generated_at}
    </div>
    """

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Rapport pédagogique — {user_id}</title>
    <style>{css}</style>
</head>
<body>
<div class="container">
    {header}
    {exec_summary}
    {kpis}
    {mastery_table}
    {profile_section}
    {patterns_section}
    {recommendations}
    {problematic_section}
    {footer}
</div>
</body>
</html>"""


# ── Point d'entrée ─────────────────────────────────────────────────────────────

def generate_report(user_id: str, output_dir: Path) -> Path:
    """Génère le rapport HTML. Retourne le chemin du fichier créé."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_str     = datetime.now().strftime("%Y%m%d")

    print(f"  Collecte des données pour : {user_id} ...")
    data = _collect(user_id)

    print(f"  Génération HTML ...")
    html = _build_html(data, generated_at)

    safe_uid  = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    filename  = output_dir / f"rapport_{safe_uid}_{date_str}.html"
    filename.write_text(html, encoding="utf-8")

    return filename


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère un rapport pédagogique HTML par utilisateur. Read-only."
    )
    parser.add_argument(
        "--user_id",
        default="default",
        help="Identifiant utilisateur (défaut : default)",
    )
    parser.add_argument(
        "--output_dir",
        default=str(ROOT / "reports"),
        help="Répertoire de sortie (défaut : reports/)",
    )
    args = parser.parse_args()

    init_db()
    output_dir = Path(args.output_dir)

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  RAPPORT PÉDAGOGIQUE — ADDISCO OPS")
    print(f"  Utilisateur : {args.user_id}")
    print(f"  Sortie      : {output_dir}")
    print(sep)

    filename = generate_report(args.user_id, output_dir)

    print(f"\n  Rapport généré : {filename}")
    print(f"  Ouvrir dans un navigateur pour visualiser.")
    print(f"  PDF : Ctrl+P → Enregistrer en PDF\n")


if __name__ == "__main__":
    main()
