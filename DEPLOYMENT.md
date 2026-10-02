# Lightweight Deployment Guide for t3.small (2 vCPU, 2GB RAM)

This guide shows how to deploy the Expense Tracker on a resource-constrained AWS t3.small instance.

## Architecture

**Optimizations for Low Memory**:
- SQLite database instead of PostgreSQL
- Local filesystem storage instead of S3
- No Redis/caching layer
- Single FastAPI process
- Alpine Linux-based Docker images
- Admin portal served by FastAPI (no separate nginx)

**Expected Resource Usage**:
- Memory: ~200-400 MB
- CPU: Minimal under normal load
- Disk: ~1-2 GB (includes database and receipts)

## Quick Start with Docker

### 1. Install Docker

```bash
# Update system
sudo yum update -y  # Amazon Linux
# or
sudo apt update && sudo apt upgrade -y  # Ubuntu

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
```

### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/expense-tracker.git
cd expense-tracker

# Configure environment
cp backend/.env.example backend/.env
nano backend/.env
```

**Minimal Configuration**:
```env
# Required
DATABASE_URL=sqlite:///./expense_tracker.db
SECRET_KEY=generate-a-strong-random-key-here

# Optional features (can skip to save resources)
USE_S3_STORAGE=False
OPENAI_API_KEY=  # Leave empty to skip AI categorization
GOOGLE_APPLICATION_CREDENTIALS=  # Leave empty to skip OCR
```

### 3. Build and Run

```bash
# Build optimized image
cd backend
docker build -t expense-api:lightweight .

# Run container
docker run -d \
  --name expense-tracker \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  --env-file .env \
  --restart unless-stopped \
  expense-api:lightweight

# Check logs
docker logs -f expense-tracker
```

### 4. Build Admin Portal

```bash
cd ../apps/admin

# Install dependencies
npm install

# Build for production
npm run build

# Copy to backend for serving
cp -r dist ../../backend/admin-dist
```

### 5. Access Application

- API: http://your-server-ip:8000
- Admin Portal: http://your-server-ip:8000/admin
- API Docs: http://your-server-ip:8000/docs

## Native Installation (Without Docker)

### 1. Install Python

```bash
sudo yum install python3.11 python3.11-pip -y  # Amazon Linux
# or
sudo apt install python3.11 python3.11-venv -y  # Ubuntu
```

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env

# Run migrations
alembic upgrade head

# Create admin user
python -c "
from app.core.database import SessionLocal
from app.models import User, UserRole
from app.core.security import get_password_hash

db = SessionLocal()
admin = User(
    email='admin@example.com',
    hashed_password=get_password_hash('admin123'),
    full_name='Admin User',
    role=UserRole.ADMIN
)
db.add(admin)
db.commit()
print('Admin user created: admin@example.com / admin123')
"

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Setup Systemd Service

```bash
sudo nano /etc/systemd/system/expense-api.service
```

```ini
[Unit]
Description=Expense Tracker API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/expense-tracker/backend
Environment="PATH=/home/ec2-user/expense-tracker/backend/venv/bin"
ExecStart=/home/ec2-user/expense-tracker/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable expense-api
sudo systemctl start expense-api
sudo systemctl status expense-api
```

## Memory Optimization Tips

### 1. Limit Uvicorn Workers

For t3.small, use a single worker:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 2. Enable Swap (Emergency Buffer)

```bash
# Create 2GB swap file
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Monitor Resource Usage

```bash
# Check memory
free -h

# Check disk
df -h

# Check running processes
htop  # install: sudo yum install htop -y

# Check Docker stats
docker stats expense-tracker
```

## Nginx Reverse Proxy (Optional)

For production, add nginx in front:

```bash
sudo yum install nginx -y

sudo nano /etc/nginx/conf.d/expense.conf
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
```

## SSL with Let's Encrypt

```bash
sudo yum install certbot python3-certbot-nginx -y

sudo certbot --nginx -d your-domain.com
```

## Backup Strategy

### Database Backup

```bash
# Backup SQLite database
cp backend/expense_tracker.db backend/backups/expense_tracker_$(date +%Y%m%d).db

# Automated daily backup
echo "0 2 * * * cp /home/ec2-user/expense-tracker/backend/expense_tracker.db /home/ec2-user/backups/expense_tracker_\$(date +\%Y\%m\%d).db" | crontab -
```

### Receipts Backup

```bash
# Backup uploads directory
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz backend/uploads/

# Optional: sync to S3 for off-site backup
aws s3 sync backend/uploads/ s3://your-backup-bucket/receipts/
```

## Django ERP Integration

### Setup on Django Side

```python
# Django settings.py
EXPENSE_TRACKER_API_URL = 'http://your-expense-server:8000'
EXPENSE_TRACKER_API_TOKEN = 'your-jwt-token-here'
```

### Daily Import Cron Job

```bash
# On Django server
crontab -e

# Add line to import expenses daily at 3 AM
0 3 * * * cd /path/to/django-erp && /path/to/venv/bin/python manage.py import_expenses --days 1
```

### Enable Webhook (Real-time)

In Expense Tracker `.env`:
```env
WEBHOOK_ENABLED=True
WEBHOOK_URL=https://your-erp-domain.com/api/webhook/expenses
WEBHOOK_SECRET=shared-secret-key
```

## Monitoring

### Health Check Script

```bash
nano ~/check-expense-api.sh
```

```bash
#!/bin/bash
HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): Service is healthy"
else
    echo "$(date): Service is down (HTTP $RESPONSE), restarting..."
    docker restart expense-tracker
    # or: sudo systemctl restart expense-api
fi
```

```bash
chmod +x ~/check-expense-api.sh

# Run every 5 minutes
crontab -e
*/5 * * * * ~/check-expense-api.sh >> ~/expense-api-health.log 2>&1
```

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker logs expense-tracker
# or
sudo journalctl -u expense-api -f

# Common issues:
# - Port 8000 already in use: sudo lsof -i :8000
# - Database locked: rm backend/expense_tracker.db-journal
# - Permission issues: sudo chown -R $USER:$USER backend/
```

### High Memory Usage

```bash
# Check what's using memory
docker stats

# Restart to clear memory
docker restart expense-tracker

# Check for memory leaks in logs
docker logs expense-tracker | grep -i "memory\|oom"
```

### Slow Performance

```bash
# Check disk space
df -h

# Optimize SQLite database
sqlite3 backend/expense_tracker.db "VACUUM;"

# Check slow queries
sqlite3 backend/expense_tracker.db ".mode column" ".timer on" "SELECT * FROM expenses ORDER BY created_at DESC LIMIT 100;"
```

## Scaling Up Later

When you outgrow t3.small:

1. **Upgrade to t3.medium** (4GB RAM):
   - Add second uvicorn worker
   - Enable Redis caching
   - Consider PostgreSQL

2. **Add Load Balancer**:
   - Multiple application servers
   - AWS ALB for high availability

3. **Separate Services**:
   - Move database to RDS
   - Use S3 for receipts
   - Add ElastiCache Redis

## Cost Estimate

**Monthly costs on AWS**:
- t3.small EC2: ~$15-20/month
- 20GB EBS storage: ~$2/month
- Data transfer: ~$1-2/month
- **Total: ~$18-24/month**

Optional add-ons:
- OpenAI API: ~$5-20/month (usage-based)
- Google Cloud Vision: ~$2-10/month (usage-based)

## Security Checklist

- [x] Change default SECRET_KEY
- [x] Use strong admin password
- [x] Enable firewall: `sudo ufw allow 8000/tcp`
- [x] Keep system updated: `sudo yum update -y`
- [x] Use HTTPS in production (Let's Encrypt)
- [x] Backup database regularly
- [x] Monitor logs for errors
- [x] Restrict access to sensitive files

## Support

For issues:
1. Check logs first
2. Review troubleshooting section
3. Verify resource usage
4. Check GitHub issues
