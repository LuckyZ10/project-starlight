# Starlight Deployment Guide

This directory contains deployment infrastructure for Starlight, including Nginx configuration, automated deployment scripts, and health check tools.

## Prerequisites

Before deploying Starlight, ensure you have:

1. **SSH Access**: Ability to SSH into your server
2. **Server Requirements**:
   - Linux server (Ubuntu 20.04+ recommended)
   - Docker and Docker Compose installed
   - Nginx installed
   - Public IP address or domain name
3. **SSH Key**: SSH key available at `~/.ssh/id_ed25519` (or `~/.ssh/starlight_deploy_key`)
4. **Docker Permissions**: User running Docker must be in the `docker` group

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Deploy to server
./deploy-cloud.sh <server_ip> [domain]

# Example
./deploy-cloud.sh 192.168.1.100 starlight.example.com
```

This script will:
- Set up Nginx with SSL
- Configure Docker Compose
- Install Certbot and obtain SSL certificates
- Deploy the application
- Start all services

### Option 2: Manual Deployment

#### Step 1: Prepare the Server

```bash
# SSH into your server
ssh root@your-server-ip

# Install required packages
apt update
apt install -y nginx docker.io python3-certbot-nginx

# Create deploy user
useradd -m -s /bin/bash starlight
echo "starlight:$(openssl rand -base64 32)" | chpasswd
usermod -aG docker starlight

# Set up directories
mkdir -p /opt/starlight
mkdir -p /var/log/starlight
```

#### Step 2: Deploy Application

```bash
# Copy application to server
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude 'web/frontend/.next' \
    . starlight@your-server-ip:/opt/starlight/

# SSH as starlight user
ssh starlight@your-server-ip

# Copy docker-compose.prod.yml (adjust paths if needed)
cd /opt/starlight
cp docker-compose.yml docker-compose.prod.yml
```

#### Step 3: Setup Nginx

```bash
# Copy Nginx configuration
cat > /etc/nginx/sites-available/starlight << 'EOF'
# Paste nginx.conf from this directory
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/starlight /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Restart Nginx
systemctl restart nginx
```

#### Step 4: Setup SSL with Certbot

```bash
# Request SSL certificate
certbot --nginx -d your-domain.com \
    --non-interactive --agree-tos --email admin@your-domain.com

# Enable auto-renewal
systemctl enable certbot.timer
systemctl start certbot.timer
```

#### Step 5: Start Services

```bash
cd /opt/starlight
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml ps
```

## Health Checks

### Check Service Health

```bash
# Run health check script
./deploy/healthcheck.sh

# Or with custom parameters
./deploy/healthcheck.sh \
    -u http://your-server:8000/api/health \
    -d your-domain.com \
    -t 30
```

The health check script verifies:
- Docker services running
- Backend API health
- Nginx status
- Port availability
- SSL certificate validity

### Manual Health Checks

```bash
# Check backend health
curl http://localhost:8000/api/health

# Check Nginx status
systemctl status nginx

# Check Docker containers
docker-compose ps

# Check logs
docker-compose logs -f
```

## SSL Certificate Management

### Manual Certificate Renewal

```bash
certbot renew --dry-run  # Test renewal
certbot renew            # Actual renewal
```

### Auto-Renewal

Certbot auto-renewal is configured to run every 12 hours:

```bash
# Check timer status
systemctl status certbot.timer

# View renewal logs
journalctl -u certbot.timer
```

### Certificate Expiry Alerts

Certificates expiring within 30 days will trigger warnings.

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Restart services
docker-compose restart

# Rebuild
docker-compose up -d --build
```

### Nginx Issues

```bash
# Test Nginx configuration
nginx -t

# Restart Nginx
systemctl restart nginx

# Check Nginx logs
tail -f /var/log/nginx/starlight-error.log
```

### SSL Certificate Issues

```bash
# Check certificate status
certbot certificates

# Revoke certificate
certbot revoke --non-interactive --agree-tos --delete-after-revoke

# Renew certificate
certbot renew
```

### Port Conflicts

```bash
# Check what's using a port
netstat -tuln | grep :8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

## Monitoring

### Enable Logging

```bash
# Configure Nginx log rotation
cat > /etc/logrotate.d/starlight << 'EOF'
/var/log/nginx/starlight-*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
EOF

# Restart logrotate
logrotate -f /etc/logrotate.d/starlight
```

### Set Up Monitoring

```bash
# Install monitoring tools
apt install -y htop iotop nethogs

# Monitor system resources
htop

# Monitor Docker resources
docker stats
```

## Security Hardening

### Update Firewall Rules

```bash
# UFW (Ubuntu)
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Firewalld (RHEL/CentOS)
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

### Configure Rate Limiting

Edit `nginx.conf` and add rate limiting:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://starlight_backend/api/;
    # ... other settings
}
```

## Maintenance

### Update Application

```bash
ssh starlight@your-server-ip

cd /opt/starlight

# Pull latest changes (if using git)
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Run health check
docker-compose exec backend python -m pytest
```

### Database Backup

```bash
# Backup database
docker-compose exec backend python -c "
from database import SessionLocal, engine
from sqlalchemy import text
with SessionLocal() as db:
    db.execute(text('VACUUM FULL'))
    db.commit()
"

# Backup volume
docker run --rm -v starlight-db:/data -v $(pwd):/backup \
    alpine tar czf /backup/starlight-db-$(date +%Y%m%d).tar.gz -C /data .
```

### Database Restore

```bash
# Restore database
docker run --rm -v starlight-db:/data -v $(pwd):/backup \
    alpine tar xzf /backup/starlight-db-<date>.tar.gz -C /data
```

## Support

For issues or questions:
1. Check the health check output
2. Review Nginx and Docker logs
3. Verify SSL certificate status
4. Check system resources

See `healthcheck.sh` for automated troubleshooting.

## Version History

- **v1.0.0** (2026-04-10)
  - Initial deployment infrastructure
  - Nginx configuration with SSL
  - Automated deployment script
  - Health check system
  - Certbot auto-renewal setup
