"""
Constantes de présentation : CSS global et header HTML de l'application.
Aucune dépendance Streamlit — importable indépendamment.
"""

APP_CSS = """
<style>
/* ── App background ── */
.stApp {
    background-color: #f5f6fa;
}
/* ── Main content ── */
.main .block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    background-color: #f5f6fa;
}
/* ── Tabs background ── */
.stTabs [data-baseweb="tab-panel"] {
    background-color: #f5f6fa;
    padding-top: 10px !important;
}
/* ── Dividers ── */
hr {
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
    border-color: #e2e8f0 !important;
}
/* ── Alerts ── */
[data-testid="stAlert"] {
    padding: 0.6rem 1rem !important;
    border-radius: 8px !important;
}
/* ── Tabs ── */
.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important;
    padding: 6px 16px !important;
    font-size: 13px !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 2px !important;
    border-bottom: 2px solid #e2e8f0 !important;
    background-color: transparent !important;
}
/* ── Metric labels ── */
[data-testid="stMetricLabel"] > div {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: #94a3b8 !important;
}
[data-testid="stMetricValue"] > div {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}
/* ── Bordered containers — card with shadow ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(15,23,42,.08), 0 1px 2px rgba(15,23,42,.04) !important;
    background: #ffffff !important;
    border-color: #e2e8f0 !important;
}
/* ── Caption ── */
[data-testid="stCaptionContainer"] {
    margin-bottom: 0 !important;
}
/* ── Progress bar ── */
[data-testid="stProgress"] {
    margin-bottom: 2px !important;
}
/* ── Info box border ── */
[data-testid="stAlert"][kind="info"] {
    background-color: #f0f4ff !important;
    border-left-color: #4f46e5 !important;
}
/* ── Expander ── */
[data-testid="stExpander"] {
    border-radius: 8px !important;
    border-color: #e2e8f0 !important;
    background: #ffffff !important;
}
</style>
"""

RESPONSIVE_CSS = """
<style>
/* ── Tablette (≤ 900px) ── */
@media (max-width: 900px) {
    .main .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        min-width: calc(50% - 8px) !important;
        flex: 0 0 calc(50% - 8px) !important;
    }
    .pipeline-pills-row {
        display: none !important;
    }
    [data-testid="stMetricValue"] > div {
        font-size: 1.3rem !important;
    }
}
/* ── Mobile (≤ 600px) ── */
@media (max-width: 600px) {
    [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        min-width: 100% !important;
        flex: 0 0 100% !important;
    }
}
</style>
"""

PRESENTATION_CSS = """
<style>
/* ── Mode présentation ── */
.main .block-container {
    max-width: 100% !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
}
.pipeline-pills-row {
    display: none !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.5rem !important;
}
</style>
"""

PRESENTATION_BANNER = """
<div style="background:#4f46e5;color:#fff;padding:7px 18px;border-radius:8px;
            font-size:12px;font-weight:700;letter-spacing:.08em;text-align:center;
            margin-bottom:10px;text-transform:uppercase">
    🎯 MODE PRÉSENTATION &nbsp;·&nbsp; F11 pour plein écran navigateur
</div>
"""

APP_HEADER = """
<div style="padding:6px 0 16px;border-bottom:2px solid #e2e8f0;margin-bottom:8px;background:#f5f6fa">
  <div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:9px">
    <div style="width:4px;min-height:40px;background:#4f46e5;border-radius:3px;flex-shrink:0;margin-top:2px"></div>
    <div>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:3px">
        <span style="font-size:22px;font-weight:800;color:#0f172a;letter-spacing:-0.03em;line-height:1">ADDISCO OPS</span>
        <span style="font-size:10px;font-weight:700;color:#4f46e5;text-transform:uppercase;letter-spacing:.1em;background:#eef2ff;padding:2px 9px;border-radius:20px;border:1px solid #c7d2fe;white-space:nowrap">Adaptive Learning Intelligence</span>
      </div>
      <div style="font-size:11.5px;color:#94a3b8;font-weight:500;margin-top:2px">
        RAG documentaire &middot; R&eacute;p&eacute;tition espac&eacute;e &middot; Adaptation cognitive
      </div>
    </div>
  </div>
  <div class="pipeline-pills-row" style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-left:18px">
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">&#128196; Document</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">&#128269; RAG</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">&#10067; Question</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">&#9997;&#65039; R&eacute;ponse</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">&#9989; Correction</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;padding:2px 10px;font-size:11px;color:#475569;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.04)">&#129504; M&eacute;moire</span>
    <span style="color:#c7d2fe;font-size:12px;font-weight:700">&rarr;</span>
    <span style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:20px;padding:2px 10px;font-size:11px;color:#4f46e5;white-space:nowrap;font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,.04)">&#128260; R&eacute;vision</span>
  </div>
</div>
"""
