@echo off
title ADDISCO OPS - Lancement
cd /d "%~dp0"

echo ==========================================
echo ADDISCO OPS - Lancement demo
echo ==========================================
echo.

if exist ".venv\Scripts\activate.bat" (
    echo Activation de l'environnement virtuel...
    call ".venv\Scripts\activate.bat"
) else (
    echo Aucun environnement virtuel local trouve.
    echo Utilisation du Python systeme.
)

echo.
echo Verification de Streamlit...
python -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Streamlit n'est pas installe.
    echo Lance d'abord:
    echo pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Lancement de l'application...
echo URL: http://localhost:8501
echo.

python -m streamlit run app.py --server.port 8501

echo.
echo L'application s'est arretee.
pause
