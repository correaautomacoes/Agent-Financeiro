#!/bin/bash

echo "=================================================="
echo "    ATUALIZADOR AUTOMÁTICO - VPS"
echo "=================================================="
echo ""

# Se você estiver usando Git, descomente a linha abaixo para baixar as mudanças antes de buildar:
# git pull origin main

echo "[1/2] Reconstruindo a imagem com os novos ajustes..."
docker compose up -d --build

echo "[2/2] Limpando imagens antigas (opcional)..."
docker image prune -f

echo ""
echo "=================================================="
echo "    SISTEMA ATUALIZADO COM SUCESSO! 🚀"
echo "=================================================="
echo "As alterações já estão no ar."
echo ""
