# Expense Tracker Backend

FastAPI backend for the expense tracking system with **FREE Tesseract OCR** and **OpenAI integration** (included with ChatGPT Business).

## Key Features - Zero Extra Cost!

- ✅ **FREE Tesseract OCR** - Open-source receipt text extraction
- ✅ **OpenAI API** - Uses your ChatGPT Business subscription ($0 extra)
- ✅ **SQLite Database** - No database server needed
- ✅ **Local Storage** - No S3 costs
- JWT authentication
- Approval workflow management
- GL account mapping for ERP integration
- CSV/JSON export for accounting systems
- Comprehensive audit logging

## Quick Start

### 1. Install Tesseract (FREE)

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt install tesseract-ocr

# Windows - download from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

See [TESSERACT_SETUP.md](TESSERACT_SETUP.md) for details.

### 2. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
# REQUIRED
DATABASE_URL=sqlite:///./expense_tracker.db
SECRET_KEY=your-random-secret-here

# FREE OCR (default)
OCR_ENGINE=tesseract

# OPTIONAL: AI categorization (included with ChatGPT Business)
OPENAI_API_KEY=sk-your-api-key-here
```

**Get OpenAI API key**: See [OPENAI_SETUP.md](OPENAI_SETUP.md)

### 4. Setup Database and Run

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Access at http://localhost:8000

## Features

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   │   ├── auth.py      # Authentication
│   │   ├── expenses.py  # Expense CRUD + approval
│   │   ├── categories.py
│   │   ├── gl_accounts.py
│   │   └── admin.py     # Admin functions + export
│   ├── core/
│   │   ├── config.py    # Settings
│   │   ├── database.py  # DB connection
│   │   └── security.py  # JWT + password hashing
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   │   ├── ocr.py       # Google Cloud Vision
│   │   ├── ai.py        # OpenAI categorization
│   │   └── storage.py   # S3 file upload
│   └── middleware/
│       └── auth.py      # JWT middleware
├── alembic/             # Database migrations
└── tests/
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_expenses.py
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# View migration history
alembic history
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| SECRET_KEY | JWT secret key | Yes |
| OPENAI_API_KEY | OpenAI API key for categorization | No |
| GOOGLE_APPLICATION_CREDENTIALS | Path to GCP service account JSON | No |
| AWS_ACCESS_KEY_ID | AWS access key for S3 | Yes |
| AWS_SECRET_ACCESS_KEY | AWS secret key for S3 | Yes |
| S3_BUCKET_NAME | S3 bucket name | Yes |
| S3_ENDPOINT_URL | S3 endpoint (for MinIO) | No |

## API Examples

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure123",
    "full_name": "John Doe",
    "role": "operations"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "email=user@example.com&password=secure123"
```

### Expenses

```bash
# Create expense
curl -X POST http://localhost:8000/api/v1/expenses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 42.50,
    "currency": "USD",
    "description": "Office supplies",
    "merchant_name": "Staples",
    "expense_date": "2026-10-01",
    "category_id": "uuid"
  }'

# Approve expenses (admin)
curl -X POST http://localhost:8000/api/v1/expenses/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "expense_ids": ["uuid1", "uuid2"]
  }'
```

### Export

```bash
# Export to CSV
curl -X POST http://localhost:8000/api/v1/admin/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-10-01",
    "end_date": "2026-10-31",
    "format": "csv"
  }' > expenses.csv
```

## Production Deployment

### Docker

```bash
docker build -t expense-backend .
docker run -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e SECRET_KEY=$SECRET_KEY \
  expense-backend
```

### Systemd Service

Create `/etc/systemd/system/expense-api.service`:

```ini
[Unit]
Description=Expense Tracker API
After=network.target

[Service]
Type=notify
User=expense
WorkingDirectory=/opt/expense-backend
Environment="PATH=/opt/expense-backend/venv/bin"
ExecStart=/opt/expense-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.expense.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Performance

- Use connection pooling for database
- Enable Redis caching for frequent queries
- Configure Celery for async tasks (OCR, AI)
- Use CDN for receipt images (CloudFront)

## Security

- JWT tokens expire after 30 minutes
- Passwords hashed with bcrypt
- SQL injection protected by SQLAlchemy
- CORS configured for specific origins
- File uploads validated and scanned
- Audit logs for all mutations

## Monitoring

- Health check: `GET /health`
- Database status: Check Alembic current revision
- S3 connectivity: Test file upload
- OpenAI API: Monitor usage in dashboard

## License

MIT
