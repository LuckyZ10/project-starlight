#!/bin/bash
# Starlight Certbot Setup Script
# Automates SSL certificate setup with Let's Encrypt

set -e

# Configuration
DOMAIN="${DOMAIN:-starlight.local}"
EMAIL="${EMAIL:-admin@starlight.local}"
STAGING="${STAGING:-0}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Starlight Certbot Setup ===${NC}"
echo -e "${BLUE}Domain: ${DOMAIN}${NC}"
echo -e "${BLUE}Email: ${EMAIL}${NC}"
echo -e "${BLUE}Staging: ${STAGING}${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# 1. Install Certbot
echo -e "${BLUE}[1/5] Installing Certbot...${NC}"
apt update
apt install -y certbot python3-certbot-nginx

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Certbot installation failed${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Certbot installed"
echo ""

# 2. Stop Nginx temporarily
echo -e "${BLUE}[2/5] Stopping Nginx...${NC}"
systemctl stop nginx
echo -e "  ${GREEN}✓${NC} Nginx stopped"
echo ""

# 3. Request SSL Certificate
echo -e "${BLUE}[3/5] Requesting SSL Certificate...${NC}"
certbot certonly --nginx -d $DOMAIN --email $EMAIL --non-interactive

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ SSL certificate request failed${NC}"
    systemctl start nginx
    exit 1
fi

echo -e "  ${GREEN}✓${NC} SSL certificate obtained"
echo ""

# 4. Generate dhparams (optional but recommended)
echo -e "${BLUE}[4/5] Generating Diffie-Hellman parameters...${NC}"
if [ ! -f /etc/ssl/certs/dhparam.pem ]; then
    openssl dhparam -out /etc/ssl/certs/dhparam.pem 4096
    echo -e "  ${GREEN}✓${NC} DH parameters generated"
else
    echo -e "  ${YELLOW}⚠${NC} DH parameters already exist"
fi
echo ""

# 5. Restart Nginx
echo -e "${BLUE}[5/5] Starting Nginx...${NC}"
systemctl start nginx

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to start Nginx${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Nginx started"
echo ""

# 6. Verify Certificate
echo -e "${BLUE}=== Certificate Verification ===${NC}"
CERT_DAYS=$(openssl x509 -in /etc/letsencrypt/live/${DOMAIN}/fullchain.pem -noout -enddate | cut -d= -f2)
EXPIRY_DATE=$(date -d "$CERT_DAYS" +%Y-%m-%d)
CURRENT_DATE=$(date +%Y-%m-%d)
DAYS_REMAINING=$(( ($(date -d "$EXPIRY_DATE" +%s) - $(date +%s)) / 86400 ))

echo -e "  Certificate valid until: $CERT_DAYS"
echo -e "  Days remaining: $DAYS_REMAINING"

if [ $DAYS_REMAINING -lt 30 ]; then
    echo -e "  ${YELLOW}⚠ Warning: Certificate expires soon!${NC}"
else
    echo -e "  ${GREEN}✓ Certificate is healthy${NC}"
fi
echo ""

# 7. Setup Auto-Renewal
echo -e "${BLUE}=== Auto-Renewal Setup ===${NC}"
systemctl enable certbot.timer
systemctl start certbot.timer

echo -e "  ${GREEN}✓${NC} Certbot timer enabled and started"
echo -e "  ${GREEN}✓${NC} Auto-renewal scheduled (every 12 hours)"
echo ""

# 8. Test Renewal
echo -e "${BLUE}=== Testing Certificate Renewal ===${NC}"
certbot renew --dry-run

if [ $? -ne 0 ]; then
    echo -e "  ${RED}✗ Certificate renewal test failed${NC}"
else
    echo -e "  ${GREEN}✓${NC} Certificate renewal works correctly"
fi
echo ""

echo -e "${GREEN}=== Certbot Setup Complete ===${NC}"
echo -e "SSL Certificate: /etc/letsencrypt/live/${DOMAIN}/"
echo -e "Auto-renewal: Every 12 hours"
echo -e "Test renewal: certbot renew --dry-run"
echo -e "View certificates: certbot certificates"
