@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ==================================================
echo    INICIANDO AGENTE FINANCEIRO
echo ==================================================

set "VENV_PY=%~dp0venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    set "PYTHON=%VENV_PY%"
) else (
    set "PYTHON=python"
)

"%PYTHON%" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado.
    echo Instale o Python 3.10+ ou crie o ambiente virtual com:
    echo     python -m venv venv
    pause
    exit /b
)

set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
set "USERPROFILE=%cd%"
set "HOME=%cd%"

findstr "DB_TYPE=postgres" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo [1/2] Iniciando Docker...
    docker compose up -d >nul 2>&1
    if %errorlevel% neq 0 (
        echo [AVISO] Nao foi possivel iniciar o Docker Compose.
        echo Verifique se o Docker esta instalado e rodando.
    )
)

echo [2/2] Abrindo Streamlit...
echo.| "%PYTHON%" -m streamlit run app.py
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao iniciar o Streamlit.
    echo Verifique se o Streamlit esta instalado no venv:
    echo     .\venv\Scripts\pip install -r requirements.txt
    pause
)

endlocal
