#!/bin/bash

echo "=================================================="
echo "    INSTALADOR AUTOMÁTICO - VPS / LINUX"
echo "=================================================="
echo ""

# 1. Verificar dependências
if ! command -v docker &> /dev/null; then
    echo "[ERRO] Docker não encontrado. Por favor, instale o Docker primeiro."
    exit 1
fi

# 2. Criar .env se não existir
if [ ! -f .env ]; then
    echo "[1/3] Configurando arquivo .env..."
    cp .env.example .env
    read -p "Cole sua GEMINI_API_KEY aqui: " API_KEY
    sed -i "s/YOUR_GEMINI_KEY_HERE/$API_KEY/g" .env
fi

# 3. Subir tudo via Docker (App + DB)
echo "[2/3] Subindo Sistema e Banco via Docker Compose..."
docker compose up -d --build

# 4. Inicializar tabelas (dentro do container)
echo "[3/3] Inicializando banco de dados..."
sleep 10
docker exec -it erp_app python database.py

echo ""
echo "=================================================="
echo "    INSTALAÇÃO CONCLUÍDA! 🚀"
echo "=================================================="
echo "Acesse o sistema em: http://seu-ip-vps:8501"
echo ""
