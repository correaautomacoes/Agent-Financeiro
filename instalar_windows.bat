@echo off
setlocal
echo ==================================================
echo    INSTALADOR AUTOMATICO - AGENTE FINANCEIRO
echo ==================================================
echo.

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado! Por favor, instale o Python 3.10+
    pause
    exit /b
)

:: 2. Criar Ambiente Virtual para nao poluir o sistema do usuario
if not exist "venv" (
    echo [1/5] Criando ambiente isolado (venv)...
    python -m venv venv
)

:: 3. Instalar dependencias
echo [2/5] Instalando bibliotecas necessarias (isso pode demorar)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt >nul

:: 4. Configurar .env se nao existir
if not exist ".env" (
    echo [3/5] Configurando arquivo de chaves...
    copy .env.example .env >nul
    echo.
    set /p API_KEY="Cole sua GEMINI_API_KEY aqui: "
    powershell -Command "(gc .env) -replace 'YOUR_GEMINI_KEY_HERE', '%API_KEY%' | Out-File -encoding ASCII .env"
) else (
    echo [3/5] Arquivo .env ja existe, pulando...
)

:: 5. Iniciar Banco de Dados
echo [4/5] Iniciando Banco de Dados via Docker...
docker compose up -d
echo Aguardando banco iniciar...
timeout /t 10 /nobreak >nul

:: 6. Inicializar Tabelas
echo [5/5] Criando tabelas no banco...
python database.py

echo.
echo ==================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO! 🚀
echo ==================================================
echo Para abrir o sistema no futuro, use o arquivo 'run.bat'
echo.
pause
call streamlit run app.py
