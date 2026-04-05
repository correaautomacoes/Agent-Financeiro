#!/bin/bash
# Setup Script para Linux/macOS - Agente Financeiro
# Uso: bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  AGENTE FINANCEIRO - Setup${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 não encontrado!${NC}"
    echo "Instale com: brew install python3 (macOS) ou apt-get install python3 (Linux)"
    exit 1
fi

echo -e "${GREEN}✓ Python encontrado$(python3 --version)${NC}"

# Executar setup.py
echo -e "\n${BLUE}Iniciando instalação...${NC}\n"
python3 setup.py

echo -e "\n${GREEN}Setup concluído!${NC}"
