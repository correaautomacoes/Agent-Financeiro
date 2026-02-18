@echo off
echo ==========================================
echo      AGENTE FINANCEIRO INTELIGENTE
echo ==========================================

echo [1/5] Limpando ambiente anterior...
docker compose down

echo [2/5] Iniciando Banco de Dados (Docker)...
docker compose up -d

echo [3/5] Aguardando Banco de Dados iniciar (15s)...
timeout /t 15 /nobreak

echo [4/5] Criando Tabelas...
python database.py

echo [5/5] Iniciando Aplicacao...
python -m streamlit run app.py
