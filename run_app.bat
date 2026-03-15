@echo off
cd /d "%~dp0"
setlocal

echo ==================================================
echo    INICIANDO AGENTE FINANCEIRO
echo ==================================================

set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
set "USERPROFILE=%cd%"
set "HOME=%cd%"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado neste computador.
    echo Instale o Python 3 e tente novamente.
    pause
    exit /b
)

:: Sobe o banco se for modo Docker
findstr "DB_TYPE=postgres" .env >nul
if %errorlevel% equ 0 (
    echo [1/2] Iniciando Docker...
    docker compose up -d >nul 2>&1
)

echo [2/2] Abrindo Streamlit...
echo.| python -m streamlit run app.py
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao iniciar o Streamlit.
    pause
)
