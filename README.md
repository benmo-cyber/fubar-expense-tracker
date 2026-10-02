# Expense Tracker - Python Backend & Admin Portal

A production-ready, **lightweight** expense tracking system optimized for small servers. Features **FREE Tesseract OCR** and uses **OpenAI API (included with ChatGPT Business)** for $0 additional cost.

**Perfect for t3.small AWS instances (2 vCPU, 2GB RAM)** - uses SQLite, local storage, and minimal dependencies.

## 💰 Zero Additional Cost Setup

- ✅ **FREE Tesseract OCR** - Open-source receipt text extraction
- ✅ **OpenAI API** - Included with ChatGPT Business subscription
- ✅ **SQLite Database** - No database server costs
- ✅ **Local Storage** - No S3 costs
- **Total extra costs: $0/month** (if you have ChatGPT Business)

## Key Features

### Backend (Python/FastAPI)
- ✅ **Lightweight** - Runs on 200-400 MB RAM
- ✅ **SQLite Database** - No PostgreSQL setup needed
- ✅ **Local File Storage** - S3 optional
- ✅ **FREE Tesseract OCR** - Open-source receipt text extraction
- ✅ **OpenAI Categorization** - Uses your ChatGPT Business API key
- ✅ **JWT Authentication** with secure password hashing
- ✅ **Approval Workflow** (draft → pending → approved/rejected)
- ✅ **GL Account Mapping** for ERP integration
- ✅ **Django ERP Export** - CSV/JSON with webhook support
- ✅ **Audit Logging** for compliance
- ✅ **Alembic Migrations** for database versioning

### Admin Portal (React)
- ✅ **Modern Dashboard** with expense statistics
- ✅ **Expense Review Interface** with bulk approval/rejection
- ✅ **GL Account Mapping** - map categories to account codes
- ✅ **Responsive Design** with Tailwind CSS
- ✅ **Shadcn/ui Components** for professional UI
- ✅ **Served by FastAPI** - no separate web server needed

## Quick Start (5 minutes)

### Prerequisites

**Install Tesseract OCR (FREE):**

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

See [TESSERACT_SETUP.md](backend/TESSERACT_SETUP.md) for detailed instructions.

### Option 1: Docker (Recommended)

```bash
# Clone and configure
git clone https://github.com/yourusername/expense-tracker.git
cd expense-tracker/backend
cp .env.example .env
nano .env  # Set SECRET_KEY

# Build and run
docker build -t expense-api .
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  --env-file .env \
  expense-api

# Access at http://localhost:8000
```

### Option 2: Native Python

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env  # Set SECRET_KEY

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Access at http://localhost:8000
```

## Django ERP Integration

### Export API Endpoints

```python
# Get approved expenses
GET /api/v1/expenses/export?status=approved&start_date=2026-10-01&format=json

# Get single expense
GET /api/v1/expenses/export/{expense_id}

# Batch export
GET /api/v1/expenses/export/batch?expense_ids=uuid1,uuid2,uuid3&format=csv
```

### Django Management Command

```bash
# Auto-import approved expenses
python manage.py import_expenses --days 7
```

### Webhook Notifications (Real-time)

```env
# In Expense Tracker .env
WEBHOOK_ENABLED=True
WEBHOOK_URL=https://your-erp.com/api/webhook/expenses
WEBHOOK_SECRET=shared-secret
```

See `backend/django_integration.py` for complete Django examples.

## Resource Requirements

### Minimum (Development)
- CPU: 1 core
- RAM: 512 MB
- Disk: 1 GB

### Recommended (Production)
- CPU: 2 cores (t3.small)
- RAM: 2 GB
- Disk: 10 GB

### With All Features Enabled
- CPU: 2 cores
- RAM: 2-4 GB
- Disk: 20 GB

## Configuration

### Minimal Setup (FREE - No external dependencies)

```env
DATABASE_URL=sqlite:///./expense_tracker.db
SECRET_KEY=your-secret-key-here

# FREE Tesseract OCR (default)
OCR_ENGINE=tesseract
TESSERACT_CMD=  # Auto-detected

# Optional: OpenAI for AI categorization (included with ChatGPT Business)
OPENAI_API_KEY=  # Leave empty to skip

# Local storage (no S3 costs)
USE_S3_STORAGE=False
LOCAL_STORAGE_PATH=./uploads/receipts
```

### With ChatGPT Business (AI Categorization)

```env
# Required
DATABASE_URL=sqlite:///./expense_tracker.db
SECRET_KEY=your-secret-key-here

# FREE OCR
OCR_ENGINE=tesseract

# AI Categorization (included with ChatGPT Business)
OPENAI_API_KEY=sk-your-api-key-here
```

**Get your OpenAI API key**: See [OPENAI_SETUP.md](backend/OPENAI_SETUP.md)

### Full Setup (All features)

```env
# Required
DATABASE_URL=sqlite:///./expense_tracker.db
SECRET_KEY=your-secret-key-here

# FREE Tesseract OCR (recommended)
OCR_ENGINE=tesseract

# OR use Google Cloud Vision (paid)
# OCR_ENGINE=google
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# GCP_PROJECT_ID=your-project-id

# OpenAI for AI categorization (included with ChatGPT Business)
OPENAI_API_KEY=sk-your-key

# Storage (choose one)
USE_S3_STORAGE=False  # Local filesystem (free)
LOCAL_STORAGE_PATH=./uploads/receipts

# OR

USE_S3_STORAGE=True  # AWS S3 (paid)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=expense-receipts

# Django ERP Integration
WEBHOOK_ENABLED=True
WEBHOOK_URL=https://your-erp.com/api/webhook/expenses
WEBHOOK_SECRET=shared-secret
```

## Deployment

### AWS t3.small (Optimized)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed guide including:
- Docker deployment
- Native installation
- Systemd service setup
- Nginx reverse proxy
- SSL with Let's Encrypt
- Backup strategies
- Monitoring setup

**Cost**: ~$18-24/month on AWS

### Key Optimization Features

1. **SQLite instead of PostgreSQL** - No database server needed
2. **Local filesystem storage** - No S3 costs initially
3. **Alpine Linux Docker images** - Smaller size, faster startup
4. **Single process mode** - Minimal memory footprint
5. **Optional features** - Enable OCR/AI only if needed

## API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
```http
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Expenses
```http
GET    /expenses              # List expenses
POST   /expenses              # Create expense
POST   /expenses/scan-receipt # OCR + AI categorization
POST   /expenses/approve      # Bulk approve (admin)
POST   /expenses/reject       # Bulk reject (admin)
```

### Export (Django ERP)
```http
GET    /expenses/export           # Export with filters
GET    /expenses/export/{id}      # Single expense
GET    /expenses/export/batch     # Batch by IDs
```

### GL Accounts
```http
GET    /gl-accounts                    # List GL accounts
GET    /gl-accounts/mappings           # List category mappings
POST   /gl-accounts/mappings           # Create mapping
```

**Interactive Docs**: http://localhost:8000/docs

## Tech Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: SQLite (lightweight, no server needed)
- **Auth**: JWT with python-jose
- **OCR**: Google Cloud Vision (optional)
- **AI**: OpenAI GPT-4 (optional)
- **Storage**: Local filesystem or AWS S3

### Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **Styling**: Tailwind CSS + Shadcn/ui
- **Data**: TanStack Query
- **Routing**: React Router 6

## Development

### Backend
```bash
cd backend
uvicorn app.main:app --reload

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Frontend
```bash
cd apps/admin
npm run dev    # Development
npm run build  # Production build
```

## Production Checklist

- [ ] Change SECRET_KEY to strong random value
- [ ] Create admin user with strong password
- [ ] Enable HTTPS (Let's Encrypt)
- [ ] Setup regular database backups
- [ ] Configure firewall rules
- [ ] Setup monitoring/health checks
- [ ] Review and set CORS_ORIGINS
- [ ] Enable webhook for Django ERP (if applicable)
- [ ] Setup log rotation
- [ ] Document recovery procedures

## Django ERP Integration Guide

### 1. Install Client Library

```bash
pip install requests
```

### 2. Add to Django Settings

```python
# settings.py
EXPENSE_TRACKER_API_URL = 'http://your-expense-server:8000'
EXPENSE_TRACKER_API_TOKEN = 'your-jwt-token'
EXPENSE_TRACKER_WEBHOOK_SECRET = 'shared-secret'
```

### 3. Create Management Command

```bash
# Copy example from backend/django_integration.py
cp backend/django_integration.py yourapp/management/commands/import_expenses.py
```

### 4. Schedule Import

```bash
# Cron: Daily import at 3 AM
0 3 * * * cd /path/to/django && python manage.py import_expenses --days 1
```

### 5. Setup Webhook (Optional)

```python
# urls.py
from yourapp import views

urlpatterns = [
    path('api/webhook/expenses', views.expense_webhook),
]
```

Complete examples in `backend/django_integration.py`.

## Troubleshooting

### API Won't Start
```bash
# Check logs
docker logs expense-tracker

# Check port
sudo lsof -i :8000

# Check database
ls -lh backend/expense_tracker.db
```

### High Memory Usage
```bash
# Check usage
docker stats

# Restart
docker restart expense-tracker

# Enable swap (emergency)
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo mkswap /swapfile && sudo swapon /swapfile
```

### Database Issues
```bash
# Optimize
sqlite3 expense_tracker.db "VACUUM;"

# Backup
cp expense_tracker.db expense_tracker.backup.db

# Reset (development only!)
rm expense_tracker.db
alembic upgrade head
```

## Monitoring

```bash
# Health check
curl http://localhost:8000/health

# Check disk space
df -h

# Check memory
free -h

# View logs
docker logs -f expense-tracker
```

## Security

- JWT tokens with secure secret key
- Bcrypt password hashing
- CORS configuration
- SQL injection protection (SQLAlchemy)
- File upload validation
- Audit logging
- Optional webhook signature verification

## Backup

### Database
```bash
# Daily backup
cp expense_tracker.db backups/expense_tracker_$(date +%Y%m%d).db
```

### Receipts
```bash
# Backup uploads
tar -czf uploads_backup.tar.gz uploads/
```

### Automated
```bash
# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

## Scaling

When you outgrow a single server:

1. **Upgrade instance** - Move to t3.medium (4GB RAM)
2. **Switch to PostgreSQL** - Better for concurrent users
3. **Enable S3 storage** - Offload file storage
4. **Add Redis** - For caching and sessions
5. **Multiple workers** - Scale horizontally
6. **Load balancer** - AWS ALB for HA

## Cost Estimate

**Minimal Setup** (FREE receipts + manual categorization):
- EC2 t3.small: $15-20/month
- EBS: $2/month
- **OCR**: $0 (Tesseract is free)
- **AI**: $0 (disabled)
- **Total: ~$17-22/month**

**With ChatGPT Business** (FREE OCR + AI categorization):
- Above costs: $17-22/month
- **OCR**: $0 (Tesseract is free)
- **AI**: $0 (included with ChatGPT Business subscription)
- **Total: ~$17-22/month** (no additional cost!)

**Note**: OpenAI API usage with ChatGPT Business costs ~$1-2 per 100 receipts, but this is minimal compared to Google Cloud Vision OCR costs (~$150 per 1000 receipts).

## License

MIT License

## Support

- 📚 Documentation: See README files in backend/ and apps/admin/
- 🔧 Deployment Guide: See DEPLOYMENT.md
- 🐍 Django Integration: See backend/django_integration.py
- 🐛 Issues: GitHub Issues
- 📖 API Docs: http://your-server:8000/docs

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## Roadmap

- [ ] Email notifications
- [ ] Multi-currency exchange rates
- [ ] Bulk CSV import
- [ ] Advanced reporting
- [ ] Mobile app
- [ ] Slack/Teams integration
- [ ] Budget tracking

## Project Structure

```
expense-tracker/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/            # API endpoints
│   │   ├── core/              # Config, database, security
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic (OCR, AI, Storage)
│   │   ├── middleware/        # Auth middleware
│   │   └── main.py            # FastAPI app
│   ├── alembic/               # Database migrations
│   ├── requirements.txt
│   └── .env.example
│
└── apps/
    └── admin/                 # React admin portal
        ├── src/
        │   ├── components/    # Reusable UI components
        │   ├── pages/         # Dashboard, Expenses, GL Accounts
        │   ├── hooks/         # React Query hooks
        │   ├── lib/           # Utils and API client
        │   └── types/         # TypeScript types
        ├── package.json
        └── vite.config.ts
```

## Features

### Backend (Python/FastAPI)
- ✅ **FastAPI** with automatic OpenAPI documentation
- ✅ **PostgreSQL** database with SQLAlchemy ORM
- ✅ **JWT Authentication** with secure password hashing
- ✅ **Receipt OCR** via Google Cloud Vision API
- ✅ **AI Categorization** using OpenAI GPT-4
- ✅ **S3-Compatible Storage** for receipt images
- ✅ **Approval Workflow** (draft → pending → approved/rejected)
- ✅ **GL Account Mapping** for ERP integration
- ✅ **CSV/JSON Export** for accounting systems
- ✅ **Audit Logging** for compliance
- ✅ **Alembic Migrations** for database versioning

### Admin Portal (React)
- ✅ **Modern Dashboard** with expense statistics
- ✅ **Expense Review Interface** with bulk approval/rejection
- ✅ **GL Account Mapping** - map categories to account codes
- ✅ **Responsive Design** with Tailwind CSS
- ✅ **Shadcn/ui Components** for professional UI
- ✅ **React Query** for efficient data fetching
- ✅ **Export Functionality** integrated

## Tech Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0
- **Auth**: JWT with python-jose
- **OCR**: Google Cloud Vision API
- **AI**: OpenAI GPT-4 API
- **Storage**: AWS S3 / MinIO (S3-compatible)
- **Migrations**: Alembic

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn/ui + Radix UI
- **Data Fetching**: TanStack Query (React Query)
- **Routing**: React Router 6
- **Forms**: React Hook Form + Zod

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- AWS/MinIO for S3 storage
- Google Cloud Vision API credentials (optional)
- OpenAI API key (optional)

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run migrations
alembic upgrade head

# Start server
python -m app.main
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 2. Admin Portal Setup

```bash
cd apps/admin

# Install dependencies
npm install

# Configure API URL (optional)
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env.local

# Start dev server
npm run dev
# Portal available at http://localhost:5173
```

## Configuration

### Backend Environment Variables

Create `backend/.env` from `.env.example`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/expense_tracker

# JWT
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=expense-receipts
S3_ENDPOINT_URL=  # Optional for MinIO

# Google Cloud Vision (for OCR)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_PROJECT_ID=your-project-id

# OpenAI (for AI categorization)
OPENAI_API_KEY=sk-your-openai-api-key

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Database Setup

```bash
# Create database
createdb expense_tracker

# Or with psql
psql -U postgres
CREATE DATABASE expense_tracker;
\q

# Run migrations
cd backend
alembic upgrade head

# Create admin user (Python shell)
python
>>> from app.core.database import SessionLocal
>>> from app.models import User, UserRole
>>> from app.core.security import get_password_hash
>>> db = SessionLocal()
>>> admin = User(
...     email="admin@example.com",
...     hashed_password=get_password_hash("admin123"),
...     full_name="Admin User",
...     role=UserRole.ADMIN
... )
>>> db.add(admin)
>>> db.commit()
>>> exit()
```

## API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
```http
POST /auth/register
POST /auth/login
GET  /auth/me
PUT  /auth/me
```

### Expenses
```http
GET    /expenses              # List expenses (with filters)
POST   /expenses              # Create expense
GET    /expenses/{id}         # Get expense
PUT    /expenses/{id}         # Update expense
DELETE /expenses/{id}         # Delete expense
POST   /expenses/{id}/submit  # Submit for approval

POST   /expenses/scan-receipt # OCR + AI categorization
POST   /expenses/upload-receipt # Upload receipt image
POST   /expenses/approve      # Bulk approve (admin)
POST   /expenses/reject       # Bulk reject (admin)
```

### Categories
```http
GET    /categories           # List categories
POST   /categories           # Create (admin)
PUT    /categories/{id}      # Update (admin)
DELETE /categories/{id}      # Delete (admin)
```

### GL Accounts
```http
GET    /gl-accounts                    # List GL accounts
POST   /gl-accounts                    # Create (admin)
PUT    /gl-accounts/{id}               # Update (admin)
DELETE /gl-accounts/{id}               # Delete (admin)

GET    /gl-accounts/mappings           # List mappings
POST   /gl-accounts/mappings           # Create mapping
PUT    /gl-accounts/mappings/{id}      # Update mapping
DELETE /gl-accounts/mappings/{id}      # Delete mapping
```

### Admin
```http
GET    /admin/dashboard     # Dashboard statistics
POST   /admin/export        # Export expenses to CSV/JSON
```

### Interactive API Documentation

Visit `http://localhost:8000/docs` for Swagger UI with interactive API testing.

## Database Schema

### Core Tables

- **users** - User accounts with roles (operations, sales, admin)
- **categories** - Expense categories
- **gl_accounts** - General ledger account codes
- **gl_account_mappings** - Category → GL account mappings
- **expenses** - Expense records with approval workflow
- **expense_reports** - Monthly aggregated reports
- **report_category_breakdown** - Category breakdowns per report
- **audit_logs** - Audit trail for compliance

### Key Features

- UUID primary keys for security
- Full-text search on OCR text
- AI confidence tracking for continuous improvement
- Manual override flags
- Approval workflow states
- Automatic GL account mapping via categories

## Development

### Backend Development

```bash
cd backend

# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Frontend Development

```bash
cd apps/admin

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

## Production Deployment

### Backend (Docker)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Docker)

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

### Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: expense_user
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: expense_tracker
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://expense_user:changeme@db:5432/expense_tracker
    depends_on:
      - db

  admin:
    build: ./apps/admin
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

## ERP Integration

### Export Formats

**CSV Export**
```csv
ID,User Email,Date,Merchant,Description,Amount,Currency,Category,GL Account Code,Status,Submitted At,Approved At
...
```

**JSON Export**
```json
[
  {
    "id": "uuid",
    "user_email": "user@example.com",
    "date": "2026-10-01",
    "merchant": "Starbucks",
    "description": "Coffee meeting",
    "amount": 12.50,
    "currency": "USD",
    "category": "Meals & Entertainment",
    "gl_account_code": "6100",
    "status": "approved",
    "submitted_at": "2026-10-01T10:00:00Z",
    "approved_at": "2026-10-02T09:00:00Z"
  }
]
```

### Automation

Set up scheduled exports via cron or similar:

```bash
# Daily export of approved expenses
curl -X POST http://localhost:8000/api/v1/admin/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-10-01",
    "end_date": "2026-10-31",
    "status": "approved",
    "format": "csv"
  }' > expenses_$(date +%Y%m%d).csv
```

## Security Best Practices

1. **Change default secrets** in production
2. **Use HTTPS** for all API communication
3. **Rotate JWT secrets** regularly
4. **Enable MFA** for admin users (implement as needed)
5. **Regular backups** of PostgreSQL database
6. **Limit API rate** to prevent abuse
7. **Monitor audit logs** for suspicious activity

## Troubleshooting

### Backend Issues

**Database connection fails**
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection string
psql $DATABASE_URL
```

**OCR not working**
- Verify Google Cloud credentials are set correctly
- Check `GOOGLE_APPLICATION_CREDENTIALS` path
- Ensure Cloud Vision API is enabled in GCP

**AI categorization not working**
- Verify OpenAI API key is valid
- Check API quota/billing
- Review logs for error messages

### Frontend Issues

**API requests fail**
- Check backend is running on correct port
- Verify CORS settings in backend
- Check browser console for errors

**Build fails**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Backend: Check `/docs` endpoint for API documentation
- Frontend: Review browser console for errors
- Database: Check Alembic migration history

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Roadmap

- [ ] Email notifications for expense approvals
- [ ] Multi-currency support with exchange rates
- [ ] Bulk import from CSV
- [ ] Advanced reporting with charts
- [ ] Mobile app integration
- [ ] Slack/Teams notifications
- [ ] Recurring expense templates
- [ ] Budget tracking and alerts
