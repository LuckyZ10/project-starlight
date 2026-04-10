#!/bin/bash
# Starlight Automated Deployment Script
# Usage: ./deploy-cloud.sh <server_ip> [domain]
# Example: ./deploy-cloud.sh 192.168.1.100 starlight.example.com

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVER_IP=${1}
DOMAIN=${2:-starlight.local}

if [ -z "$SERVER_IP" ]; then
    echo -e "${RED}Error: Server IP is required${NC}"
    echo "Usage: $0 <server_ip> [domain]"
    echo "Example: $0 192.168.1.100 starlight.example.com"
    exit 1
fi

echo -e "${GREEN}=== Starlight Deployment Script ===${NC}"
echo -e "${YELLOW}Target: ${SERVER_IP}${NC}"
echo -e "${YELLOW}Domain: ${DOMAIN}${NC}"
echo ""

# Check if SSH key exists
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo -e "${RED}Error: SSH key not found at ~/.ssh/id_ed25519${NC}"
    echo "Please generate an SSH key: ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519"
    exit 1
fi

# Check if .deploy_key exists (optional SSH key for server)
DEPLOY_KEY="$HOME/.ssh/starlight_deploy_key"
if [ ! -f "$DEPLOY_KEY" ]; then
    echo -e "${YELLOW}Warning: Deploy key not found at ${DEPLOY_KEY}${NC}"
    echo "Using default SSH key (~/.ssh/id_ed25519)"
else
    chmod 600 "$DEPLOY_KEY"
fi

# Create temporary deploy script
cat > /tmp/deploy-starlight.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Starting Starlight Deployment ==="

# 1. Install Dependencies
echo "Installing dependencies..."
apt update
apt install -y nginx certbot python3-certbot-nginx docker.io

# 2. Create deploy user
echo "Creating deploy user..."
if ! id "starlight" &>/dev/null; then
    useradd -m -s /bin/bash starlight
    echo "starlight:$(openssl rand -base64 32)" | chpasswd
    usermod -aG docker starlight
fi

# 3. Create directories
echo "Creating directories..."
mkdir -p /opt/starlight
mkdir -p /var/log/starlight
mkdir -p /etc/letsencrypt/renewal-hooks/pre
mkdir -p /etc/letsencrypt/renewal-hooks/post

# 4. Copy application
echo "Copying application files..."
rsync -avz --delete \
    --exclude 'node_modules' \
    --exclude '.git' \
    --exclude 'web/frontend/.next' \
    --exclude 'web/backend/__pycache__' \
    --exclude '*.pyc' \
    -e "ssh -i $DEPLOY_KEY" \
    . starlight@$SERVER_IP:/opt/starlight/

# 5. Setup Docker Compose
echo "Setting up Docker Compose..."
ssh starlight@$SERVER_IP << 'DOCKEREOF'
cd /opt/starlight
cp docker-compose.yml docker-compose.prod.yml
DOCKEREOF

# 6. Setup Nginx
echo "Setting up Nginx..."
cat > /tmp/nginx.conf << 'NGINXEOF'
# Copy this content to /etc/nginx/sites-available/starlight
EOF

# 7. Setup Certbot
echo "Setting up Certbot..."

# 8. Start Services
echo "Starting Docker services..."
ssh starlight@$SERVER_IP << 'DOCKEREOF'
cd /opt/starlight
sudo -u starlight docker-compose -f docker-compose.prod.yml up -d --build
sudo -u starlight docker-compose -f docker-compose.prod.yml ps
DOCKEREOF

# 9. Setup SSL
echo "Setting up SSL certificates..."

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo "Access your application at: https://${DOMAIN}"
echo "Health check: https://${DOMAIN}/health"
EOF

chmod +x /tmp/deploy-starlight.sh

# Copy deploy key if it exists
if [ -f "$DEPLOY_KEY" ]; then
    scp -i "$DEPLOY_KEY" /tmp/deploy-starlight.sh starlight@$SERVER_IP:/tmp/deploy.sh
else
    scp /tmp/deploy-starlight.sh starlight@$SERVER_IP:/tmp/deploy.sh
fi

# Execute deployment
echo -e "${YELLOW}Running deployment on ${SERVER_IP}...${NC}"
echo "This may take 5-10 minutes..."

if [ -f "$DEPLOY_KEY" ]; then
    ssh -i "$DEPLOY_KEY" starlight@$SERVER_IP "bash /tmp/deploy.sh"
else
    ssh starlight@$SERVER_IP "bash /tmp/deploy.sh"
fi

# Copy actual nginx configuration
echo -e "${YELLOW}Copying Nginx configuration...${NC}"
cat > /tmp/nginx-setup.sh << 'NGINXEOF'
#!/bin/bash
set -e

SERVER_IP=$1
DOMAIN=$2
DEPLOY_KEY=$3

# Copy nginx config
cat > /tmp/starlight-nginx.conf << 'NGINXCONF'
EOF
cat /home/yilin/project-starlight/deploy/nginx.conf >> /tmp/starlight-nginx.conf
cat << 'NGINXCONF'
NGINXCONF

# Copy to server
if [ -n "$DEPLOY_KEY" ]; then
    scp -i "$DEPLOY_KEY" /tmp/starlight-nginx.conf root@${SERVER_IP}:/tmp/
else
    scp /tmp/starlight-nginx.conf root@${SERVER_IP}:/tmp/
fi

# Install nginx config
ssh root@${SERVER_IP} << 'ROOTEOF'
# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Copy Starlight config
cp /tmp/starlight-nginx.conf /etc/nginx/sites-available/starlight
ln -sf /etc/nginx/sites-available/starlight /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

# Restart nginx
systemctl restart nginx

# Setup Certbot
certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN}

echo "Nginx configured successfully!"
ROOTEOF

# Restart Docker services
ssh starlight@$SERVER_IP << 'DOCKEREOF'
cd /opt/starlight
sudo -u starlight docker-compose -f docker-compose.prod.yml restart
DOCKEREOF

echo -e "${GREEN}✓ Nginx and SSL configured${NC}"
echo -e "${GREEN}✓ Docker services restarted${NC}"
