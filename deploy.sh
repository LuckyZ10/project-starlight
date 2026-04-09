#!/bin/bash
# Starlight Deploy Script
# Usage: ./deploy.sh [server-ip]
# Prerequisites: Docker + docker-compose on target server

set -e

SERVER_IP=${1:-}
PROJECT_DIR="/opt/starlight"

if [ -z "$SERVER_IP" ]; then
    echo "=== Local Docker Deploy ==="
    docker compose up -d --build
    echo "✅ Starlight running at http://localhost:3000"
    echo "   Backend API at http://localhost:8000"
    exit 0
fi

echo "=== Deploying to $SERVER_IP ==="

# Copy project to server
rsync -avz --exclude='node_modules' --exclude='.next' --exclude='__pycache__' \
    --exclude='.git' ./ "${SERVER_IP}:${PROJECT_DIR}/"

# SSH and deploy
ssh "$SERVER_IP" << 'REMOTE'
cd /opt/starlight
docker compose up -d --build
docker compose ps
REMOTE

echo "✅ Deployed to $SERVER_IP"
echo "   Frontend: http://$SERVER_IP:3000"
echo "   Backend:  http://$SERVER_IP:8000"
