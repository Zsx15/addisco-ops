"""Composant StatCard — carte KPI pour le header du cockpit formateur.

Fonction pure : retourne du HTML, aucune dépendance Streamlit.
Supporte un indicateur de tendance (trend_str) optionnel sous la valeur.
"""


def stat_card_html(
    icon: str,
    label: str,
    value: str,
    color: str = "#0f172a",
    subtitle: str = "",
    alert: bool = False,
    trend_str: str = "",
) -> str:
    border = "2px solid #fca5a5" if alert else "1px solid #e2e8f0"
    bg = "#fef2f2" if alert else "#ffffff"

    if trend_str.startswith("↗"):
        t_color = "#15803d"
    elif trend_str.startswith("↘"):
        t_color = "#b91c1c" if not alert else "#b45309"
    else:
        t_color = "#94a3b8"

    sub_html = (
        f'<div style="font-size:10px;color:#94a3b8;margin-top:2px">{subtitle}</div>'
        if subtitle else ""
    )
    trend_html = (
        f'<div style="font-size:10px;font-weight:600;color:{t_color};'
        f'margin-top:4px;letter-spacing:.01em">{trend_str}</div>'
        if trend_str else ""
    )
    return (
        f'<div style="background:{bg};border:{border};border-radius:12px;'
        f'padding:14px 12px;text-align:center;'
        f'box-shadow:0 1px 3px rgba(15,23,42,.07);cursor:default;'
        f'transition:box-shadow .15s ease">'
        f'<div style="font-size:19px;line-height:1;margin-bottom:7px">{icon}</div>'
        f'<div style="font-size:25px;font-weight:800;color:{color};line-height:1;'
        f'margin-bottom:5px;letter-spacing:-0.02em">{value}</div>'
        f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.08em;color:#64748b">{label}</div>'
        f'{sub_html}'
        f'{trend_html}'
        f'</div>'
    )
