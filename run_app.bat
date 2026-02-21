@echo off
cd /d "%~dp0"

echo ==================================================
echo    INICIANDO AGENTE FINANCEIRO
echo ==================================================

if not exist "venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente venv nao encontrado.
    echo Rode o arquivo 'instalar_windows.bat' primeiro.
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
call venv\Scripts\activate.bat
streamlit run app.py
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao iniciar o Streamlit.
    pause
)
