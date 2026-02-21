@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo    INSTALADOR AGENTE FINANCEIRO
echo ==================================================
echo.

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado! Instale o Python 3.10+ e marque 'Add Python to PATH'.
    pause
    exit /b
)

:: 2. Escolha de Modo
echo Escolha o modo de instalacao:
echo [1] Desktop (Sem Docker)
echo [2] Servidor (Com Docker)
set /p MODE="Opcao (1 ou 2): "

if "%MODE%"=="2" (
    set DB_TYPE=postgres
) else (
    set DB_TYPE=sqlite
)

:: 3. Criar Ambiente Virtual
if not exist "venv" (
    echo [1/4] Criando ambiente isolado...
    python -m venv venv
)

:: 4. Instalar Dependencias
echo [2/4] Instalando bibliotecas...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 5. Configurar .env
if not exist ".env" (
    echo [3/4] Configurando arquivo de chaves...
    copy .env.example .env >nul
    echo DB_TYPE=%DB_TYPE% >> .env
    set /p KEY="Cole sua GEMINI_API_KEY: "
    echo GEMINI_API_KEY=%KEY% >> .env
)

:: 6. Banco de Dados
if "%DB_TYPE%"=="postgres" (
    echo [4/4] Iniciando Docker...
    docker compose up -d
    timeout /t 5
)
python database.py

echo ==================================================
echo    INSTALACAO CONCLUIDA!
echo ==================================================
echo Agora voce pode usar o atalho na area de trabalho.
pause
