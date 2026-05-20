"""
Capture automatique des écrans ADDISCO OPS via Playwright.

Usage (depuis la racine du projet, Streamlit déjà lancé) :
    python tools/qa/capture_screenshots.py

Prérequis :
    pip install playwright
    python -m playwright install chromium
    streamlit run app.py   ← dans un terminal séparé, sur le port 8501

Sorties : docs/assets/*.png
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

BASE_URL   = "http://localhost:8501"
ASSETS_DIR = Path(__file__).resolve().parents[2] / "docs" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Comptes de capture
ADMIN_USER   = "admin"
ADMIN_PASS   = "admin123"
LEARNER_USER = "test"
LEARNER_PASS = "test123"
APP_PASSWORD = "Demo2026"   # gate APP_PASSWORD dans .env

# Viewport large pour rendu complet
VIEWPORT = {"width": 1440, "height": 900}


def wait(page: Page, ms: int = 1500) -> None:
    page.wait_for_timeout(ms)


def wait_loaded(page: Page) -> None:
    """Attend la fin du spinner Streamlit."""
    try:
        page.wait_for_selector("[data-testid='stSpinner']", timeout=3000)
        page.wait_for_selector("[data-testid='stSpinner']", state="hidden", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(800)


def pass_app_gate(page: Page) -> None:
    """Passe le gate APP_PASSWORD si actif (détecté par aria-label)."""
    try:
        gate = page.locator("input[aria-label='Mot de passe']")
        gate.wait_for(timeout=4000)
        gate.fill(APP_PASSWORD)
        page.locator("button:has-text('Connexion')").first.click()
        wait(page, 2000)
    except Exception:
        pass  # gate absent ou déjà passé


def click_tab(page: Page, label: str) -> None:
    """Clique sur un onglet Streamlit par son texte exact."""
    page.locator(f"button[role='tab']:has-text('{label}')").first.click()
    wait(page, 1200)
    wait_loaded(page)


def _fill_form_login(page: Page, username: str, password: str) -> None:
    """Remplit et soumet le formulaire de login (username + password)."""
    # Attendre l'onglet Connexion puis le sélectionner
    page.locator("button[role='tab']:has-text('Connexion')").first.click()
    wait(page, 800)

    # Streamlit rend tous les onglets dans le DOM simultanément (visible ou non).
    # On utilise .first pour cibler les inputs du premier formulaire (Connexion).
    page.locator("input[aria-label='Nom d\\'utilisateur']").first.fill(username)
    wait(page, 300)
    page.locator("input[aria-label='Mot de passe']").first.fill(password)
    wait(page, 300)
    page.locator("button[kind='primaryFormSubmit']").first.click()
    wait(page, 2500)
    wait_loaded(page)


def login(page: Page, username: str, password: str) -> None:
    """Charge l'app, passe le gate APP_PASSWORD si nécessaire, puis se connecte."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait(page, 3000)
    pass_app_gate(page)
    wait(page, 1000)
    _fill_form_login(page, username, password)


def logout(page: Page) -> None:
    """Clique sur Déconnexion dans la sidebar."""
    try:
        page.locator("button:has-text('Déconnexion')").first.click()
        wait(page, 1500)
    except Exception:
        page.goto(BASE_URL)
        wait(page, 2000)


def screenshot(page: Page, name: str, full_page: bool = True) -> None:
    path = ASSETS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  [OK] {path.name}")


def main() -> None:
    print(f"Cible  : {BASE_URL}")
    print(f"Assets : {ASSETS_DIR}\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context(viewport=VIEWPORT)
        page    = ctx.new_page()

        # ── 1. Écran de connexion (non connecté) ─────────────────────────
        print("1. Écran de connexion")
        page.goto(BASE_URL, wait_until="networkidle")
        wait(page, 3000)
        pass_app_gate(page)
        wait(page, 1500)
        screenshot(page, "login")

        # ── 2. Session apprenant ─────────────────────────────────────────
        print("2. Connexion apprenant (test/test123)")
        login(page, LEARNER_USER, LEARNER_PASS)

        print("   >Entraînement")
        wait(page, 1000)
        screenshot(page, "session_entrainement")

        print("   >Dashboard apprenant")
        click_tab(page, "Dashboard")
        screenshot(page, "dashboard_apprenant")

        print("   >Historique")
        click_tab(page, "Historique")
        screenshot(page, "historique")

        print("   >Analytics (Moteur IA)")
        click_tab(page, "Moteur IA")
        screenshot(page, "analytics")

        logout(page)

        # ── 3. Session admin ─────────────────────────────────────────────
        print("3. Connexion admin (admin/admin123)")
        login(page, ADMIN_USER, ADMIN_PASS)

        print("   >Documents")
        click_tab(page, "Documents")
        screenshot(page, "import_documents")

        print("   >Formateur / cockpit")
        click_tab(page, "Formateur")
        screenshot(page, "dashboard_formateur")

        print("   >Dashboard admin")
        click_tab(page, "Dashboard")
        screenshot(page, "admin_roles")

        logout(page)

        browser.close()

    print(f"\nCaptures générées dans {ASSETS_DIR}")
    files = sorted(ASSETS_DIR.glob("*.png"))
    for f in files:
        size_kb = f.stat().st_size // 1024
        print(f"  {f.name:<40} {size_kb} Ko")


if __name__ == "__main__":
    main()
