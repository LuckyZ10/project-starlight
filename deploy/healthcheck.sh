#!/bin/bash
# Starlight Health Check Script
# Checks the health of Starlight application, Docker services, and Nginx

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/api/health}"
DOMAIN="${DOMAIN:-starlight.local}"
TIMEOUT="${TIMEOUT:-30}"

echo -e "${BLUE}=== Starlight Health Check ===${NC}"
echo -e "${BLUE}Health Endpoint: ${HEALTH_URL}${NC}"
echo -e "${BLUE}Timeout: ${TIMEOUT}s${NC}"
echo ""

# Counter for issues
ISSUES=0
WARNINGS=0

# 1. Check Docker Services
echo -e "${BLUE}[1/5] Checking Docker Services...${NC}"
if command -v docker-compose &> /dev/null; then
    if docker-compose -f docker-compose.yml ps | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} Docker Compose services running"
        docker-compose -f docker-compose.yml ps
    else
        echo -e "  ${RED}✗${NC} Docker Compose services not running"
        echo "  Try: docker-compose up -d"
        ((ISSUES++))
    fi
elif command -v docker &> /dev/null; then
    if docker ps | grep -q "starlight"; then
        echo -e "  ${GREEN}✓${NC} Docker containers running"
        docker ps | grep starlight
    else
        echo -e "  ${RED}✗${NC} Docker containers not running"
        echo "  Try: docker-compose up -d"
        ((ISSUES++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Docker not installed"
    ((WARNINGS++))
fi
echo ""

# 2. Check Backend Health
echo -e "${BLUE}[2/5] Checking Backend Health...${NC}"
if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m "$TIMEOUT" "$HEALTH_URL")
    if [ "$HTTP_CODE" -eq 200 ]; then
        RESPONSE=$(curl -s "$HEALTH_URL")
        echo -e "  ${GREEN}✓${NC} Backend healthy (HTTP $HTTP_CODE)"
        echo "  Response: $RESPONSE"
    elif [ "$HTTP_CODE" -eq 000 ]; then
        echo -e "  ${RED}✗${NC} Cannot connect to backend"
        echo "  Check if backend is running on port 8000"
        ((ISSUES++))
    else
        echo -e "  ${YELLOW}⚠${NC} Backend responded with HTTP $HTTP_CODE"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC} curl not installed"
    ((WARNINGS++))
fi
echo ""

# 3. Check Nginx
echo -e "${BLUE}[3/5] Checking Nginx...${NC}"
if command -v systemctl &> /dev/null; then
    NGINX_STATUS=$(systemctl is-active nginx)
    if [ "$NGINX_STATUS" == "active" ]; then
        echo -e "  ${GREEN}✓${NC} Nginx is running"
    else
        echo -e "  ${RED}✗${NC} Nginx is not running: $NGINX_STATUS"
        ((ISSUES++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC} systemctl not available"
    ((WARNINGS++))
fi
echo ""

# 4. Check Ports
echo -e "${BLUE}[4/5] Checking Ports...${NC}"

# Backend port 8000
if command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":8000 "; then
        echo -e "  ${GREEN}✓${NC} Port 8000 (Backend) is listening"
    else
        echo -e "  ${RED}✗${NC} Port 8000 is NOT listening"
        ((ISSUES++))
    fi
fi

# Frontend port 3000
if command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":3000 "; then
        echo -e "  ${GREEN}✓${NC} Port 3000 (Frontend) is listening"
    else
        echo -e "  ${YELLOW}⚠${NC} Port 3000 is NOT listening (optional for standalone)"
        ((WARNINGS++))
    fi
fi

# Nginx port 443 (HTTPS)
if command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":443 "; then
        echo -e "  ${GREEN}✓${NC} Port 443 (HTTPS) is listening"
    else
        echo -e "  ${YELLOW}⚠${NC} Port 443 (HTTPS) is NOT listening"
        ((WARNINGS++))
    fi
fi
echo ""

# 5. Check SSL Certificate
echo -e "${BLUE}[5/5] Checking SSL Certificate...${NC}"
if command -v openssl &> /dev/null; then
    CERT_DAYS=$(openssl x509 -in /etc/letsencrypt/live/${DOMAIN}/fullchain.pem -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ -n "$CERT_DAYS" ]; then
        echo -e "  ${GREEN}✓${NC} SSL Certificate valid until: $CERT_DAYS"
    else
        echo -e "  ${RED}✗${NC} SSL Certificate not found"
        echo "  Try: certbot certificates"
        ((ISSUES++))
    fi
else
    echo -e "  ${YELLOW}⚠${NC} openssl not installed"
    ((WARNINGS++))
fi
echo ""

# Summary
echo -e "${BLUE}=== Health Check Summary ===${NC}"
echo -e "  ${RED}Critical Issues: ${ISSUES}${NC}"
echo -e "  ${YELLOW}Warnings: ${WARNINGS}${NC}"
echo -e "  ${GREEN}Health: $(if [ $ISSUES -eq 0 ]; then echo "OK"; elif [ $ISSUES -le 2 ]; then echo "WARNING"; else echo "CRITICAL"; fi)${NC}"
echo ""

# Exit code
if [ $ISSUES -eq 0 ]; then
    exit 0
elif [ $ISSUES -le 2 ]; then
    exit 1
else
    exit 2
fi
