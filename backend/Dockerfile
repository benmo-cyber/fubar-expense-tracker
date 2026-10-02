FROM python:3.11-alpine

WORKDIR /app

# Install build dependencies and Tesseract OCR
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    tesseract-ocr \
    tesseract-ocr-data-eng \
    && rm -rf /var/cache/apk/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create upload directory
RUN mkdir -p uploads/receipts

# Expose port
EXPOSE 8000

# Run database migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
