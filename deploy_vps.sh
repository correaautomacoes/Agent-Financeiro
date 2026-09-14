#!/bin/bash

# ==============================================================
#   DEPLOY COMPLETO - Agente Financeiro
#   VPS Ubuntu 20.04/22.04 + Docker + Nginx + SSL Let's Encrypt
#   Domínios: erp.innovtecno.com.br | backerp.innovtecno.com.br
# ==============================================================

set -e

REPO_URL="https://github.com/correaautomacoes/Agent-Financeiro.git"
APP_DIR="$HOME/agente-financeiro"
DOMAIN_PRIMARY="erp.innovtecno.com.br"
DOMAIN_SECONDARY="backerp.innovtecno.com.br"
EMAIL="admin@innovtecno.com.br"   # Usado pelo Let's Encrypt para notificações

# ─── Cores para output ──────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m' # No Color

step() { echo -e "\n${CYAN}[$1]${NC} $2"; }
ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "  ${RED}❌ $1${NC}"; exit 1; }

echo ""
echo -e "${CYAN}=================================================="
echo -e "   DEPLOY - Agente Financeiro (HTTPS + Nginx)"
echo -e "==================================================${NC}"
echo ""

# ─── PRÉ-REQUISITOS ─────────────────────────────────────────
step "0/6" "Verificando pré-requisitos..."

command -v docker  &>/dev/null || err "Docker não encontrado! Instale com: curl -fsSL https://get.docker.com | sh"
command -v git     &>/dev/null || err "Git não encontrado! Instale com: apt install git -y"

# Garante que docker compose V2 está disponível
docker compose version &>/dev/null || err "Docker Compose V2 não encontrado!"
ok "Docker e Git OK"

# ─── 1. CLONAR / ATUALIZAR REPO ─────────────────────────────
step "1/6" "Sincronizando repositório..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git pull origin main
    ok "Repositório atualizado"
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
    ok "Repositório clonado em $APP_DIR"
fi

# ─── 2. CONFIGURAR .env ─────────────────────────────────────
step "2/6" "Configurando .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.vps.example" "$APP_DIR/.env"
    echo ""
    read -p "  ➤ Cole sua GEMINI_API_KEY aqui: " GEMINI_KEY
    sed -i "s/SUA_CHAVE_AQUI/$GEMINI_KEY/g" "$APP_DIR/.env"
    ok ".env criado com sucesso"
else
    warn ".env já existe — mantendo configuração atual"
fi

# ─── 3. BUILD DA IMAGEM ─────────────────────────────────────
step "3/6" "Fazendo build da imagem Docker..."
docker build -f Dockerfile.sqlite -t agente-financeiro .
ok "Imagem criada com sucesso"

# ─── 4. EMITIR CERTIFICADO SSL (Let's Encrypt) ──────────────
step "4/6" "Emitindo certificado SSL..."

# Verifica se já existe certificado válido
if [ -d "/var/lib/docker/volumes/agente-financeiro_certbot-conf/_data/live/$DOMAIN_PRIMARY" ]; then
    warn "Certificado já existe — pulando emissão"
else
    echo "  Subindo Nginx temporário (HTTP only) para validação..."

    # Sobe Nginx com config apenas HTTP para o Certbot fazer o challenge
    docker run -d --rm \
        --name certbot_nginx_tmp \
        -p 80:80 \
        -v "$(pwd)/nginx/nginx-init.conf:/etc/nginx/conf.d/default.conf:ro" \
        -v "agente-financeiro_certbot-www:/var/www/certbot" \
        nginx:alpine

    sleep 3

    echo "  Solicitando certificado para: $DOMAIN_PRIMARY e $DOMAIN_SECONDARY"

    docker run --rm \
        -v "agente-financeiro_certbot-conf:/etc/letsencrypt" \
        -v "agente-financeiro_certbot-www:/var/www/certbot" \
        certbot/certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email "$EMAIL" \
            --agree-tos \
            --no-eff-email \
            -d "$DOMAIN_PRIMARY" \
            -d "$DOMAIN_SECONDARY"

    # Para o Nginx temporário
    docker stop certbot_nginx_tmp 2>/dev/null || true

    ok "Certificado SSL emitido com sucesso!"
fi

# ─── 5. SUBIR STACK COMPLETA ────────────────────────────────
step "5/6" "Subindo stack completa (App + Nginx + Certbot)..."
docker compose -f docker-compose.prod.yaml down --remove-orphans 2>/dev/null || true
docker compose -f docker-compose.prod.yaml up -d
ok "Stack no ar!"

# ─── 6. STATUS FINAL ────────────────────────────────────────
step "6/6" "Verificando status dos containers..."
sleep 5
docker compose -f docker-compose.prod.yaml ps

echo ""
echo -e "${GREEN}=================================================="
echo -e "   DEPLOY CONCLUÍDO COM SUCESSO! 🎉"
echo -e "==================================================${NC}"
echo ""
echo -e "  🌐 Acesse:"
echo -e "     ${CYAN}https://$DOMAIN_PRIMARY${NC}"
echo -e "     ${CYAN}https://$DOMAIN_SECONDARY${NC}"
echo ""
echo -e "  📋 Comandos úteis:"
echo "     Ver logs app:    docker logs -f agente_financeiro"
echo "     Ver logs nginx:  docker logs -f agente_nginx"
echo "     Parar tudo:      docker compose -f $APP_DIR/docker-compose.prod.yaml down"
echo "     Atualizar:       cd $APP_DIR && git pull && docker compose -f docker-compose.prod.yaml up -d --build"
echo ""
echo -e "  🔒 Renovação SSL: automática via Certbot (container rodando em background)"
echo ""
