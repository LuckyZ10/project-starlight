#!/bin/bash
# Starlight Cloud Deploy Script
# Usage: ./deploy-cloud.sh <server-ip> [domain]
# Prerequisites: Docker + docker-compose on target server

set -euo pipefail

SERVER_IP=${1:?"Usage: $0 <server-ip> [domain]"}
DOMAIN=${2:-}
PROJECT_DIR="/opt/starlight"
SSH_OPTS="-o StrictHostKeyChecking=accept-new"

echo "=== 🚀 Deploying Starlight to $SERVER_IP ==="

# 1. Copy project files
echo "📦 Syncing project files..."
rsync -avz --exclude='node_modules' --exclude='.next' --exclude='__pycache__' \
    --exclude='.git' --exclude='venv' --exclude='*.db' \
    -e "ssh $SSH_OPTS" ./ "${SERVER_IP}:${PROJECT_DIR}/"

# 2. Setup server
echo "🔧 Setting up server..."
ssh $SSH_OPTS "$SERVER_IP" bash -s << REMOTE
set -e

# Install Docker if missing
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker \$USER
fi

# Install docker-compose plugin if missing
if ! docker compose version &> /dev/null; then
    echo "Installing docker-compose plugin..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# Configure firewall
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "✅ Firewall configured"
fi

# Create ssl dir
mkdir -p ${PROJECT_DIR}/nginx/ssl

# Deploy
cd ${PROJECT_DIR}
docker compose -f docker-compose.prod.yml down || true
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "⏳ Waiting for services to start..."
sleep 10
docker compose -f docker-compose.prod.yml ps

REMOTE

# 3. SSL setup if domain provided
if [ -n "$DOMAIN" ]; then
    echo "🔐 Setting up SSL for $DOMAIN..."
    ssh $SSH_OPTS "$SERVER_IP" bash -s << REMOTE_SSL
set -e
cd ${PROJECT_DIR}

# Update nginx config with domain
sed -i "s/server_name _;/server_name ${DOMAIN};/" nginx/nginx.conf

# Get SSL cert
docker compose -f docker-compose.prod.yml run --rm certbot \
    certonly --webroot -w /var/www/certbot \
    -d ${DOMAIN} --email admin@${DOMAIN} --agree-tos --non-interactive

echo "✅ SSL certificate obtained for ${DOMAIN}"
echo "Uncomment the HTTPS server block in nginx/nginx.conf and redeploy"
REMOTE_SSL
fi

echo ""
echo "✅ =========================================="
echo "   Starlight deployed successfully!"
echo "   Frontend: http://${DOMAIN:-$SERVER_IP}"
echo "   API:      http://${DOMAIN:-$SERVER_IP}/api/"
echo "   =========================================="
