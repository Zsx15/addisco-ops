@echo off
chcp 65001 >nul
title ADDISCO OPS — Lancement

cd /d "%~dp0"

echo.
echo  =============================================
echo   ADDISCO OPS — Demarrage
echo  =============================================
echo.

REM ── Activation environnement virtuel ─────────────────────────────────────────
if exist ".venv\Scripts\activate.bat" (
    echo  [OK] Environnement virtuel detecte.
    call .venv\Scripts\activate.bat
) else (
    echo  [INFO] Pas de .venv — Python systeme utilise.
)

echo.

REM ── Verification Python ───────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Python introuvable.
    echo  Installez Python 3.11+ depuis https://www.python.org
    echo.
    pause
    exit /b 1
)

REM ── Verification Streamlit ────────────────────────────────────────────────────
streamlit --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Streamlit introuvable.
    echo  Executez d abord : pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo  [OK] Streamlit pret.
echo.
echo  -----------------------------------------------
echo   Adresse : http://localhost:8501
echo   Le navigateur va s ouvrir automatiquement.
echo   Pour arreter : Ctrl+C ou fermer cette fenetre.
echo  -----------------------------------------------
echo.

streamlit run app.py --server.port 8501 --server.headless false

REM ── Maintien fenetre en cas d erreur ou arret ────────────────────────────────
echo.
echo  L application s est arretee.
pause
