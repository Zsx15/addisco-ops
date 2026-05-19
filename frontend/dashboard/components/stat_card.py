"""Composant StatCard — carte KPI pour le header du cockpit formateur.

Fonction pure : retourne du HTML, aucune dépendance Streamlit.
"""


def stat_card_html(
    icon: str,
    label: str,
    value: str,
    color: str = "#0f172a",
    subtitle: str = "",
    alert: bool = False,
) -> str:
    border = "2px solid #fca5a5" if alert else "1px solid #e2e8f0"
    bg = "#fef2f2" if alert else "#ffffff"
    sub_html = (
        f'<div style="font-size:10px;color:#94a3b8;margin-top:2px">{subtitle}</div>'
        if subtitle
        else ""
    )
    return (
        f'<div style="background:{bg};border:{border};border-radius:12px;'
        f'padding:16px 14px;text-align:center;'
        f'box-shadow:0 1px 3px rgba(15,23,42,.07)">'
        f'<div style="font-size:20px;line-height:1;margin-bottom:8px">{icon}</div>'
        f'<div style="font-size:26px;font-weight:800;color:{color};line-height:1;'
        f'margin-bottom:6px;letter-spacing:-0.02em">{value}</div>'
        f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.08em;color:#64748b">{label}</div>'
        f'{sub_html}'
        f'</div>'
    )
