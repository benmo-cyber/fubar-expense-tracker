from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Expense Tracker API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "sqlite:///./expense_tracker.db"
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Storage configuration - S3 optional, local filesystem default
    USE_S3_STORAGE: bool = False
    LOCAL_STORAGE_PATH: str = "./uploads/receipts"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "expense-receipts"
    S3_ENDPOINT_URL: str = ""
    
    # OCR Configuration (Tesseract is free and default)
    OCR_ENGINE: str = "tesseract"  # "tesseract" or "google" or "none"
    TESSERACT_CMD: str = ""  # Path to tesseract executable (auto-detect if empty)
    
    # Google Cloud Vision (Optional - only if OCR_ENGINE=google)
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GCP_PROJECT_ID: str = ""
    
    # OpenAI Configuration (RECOMMENDED - included with ChatGPT Business)
    # Get your API key from: https://platform.openai.com/account/api-keys
    # (Available with ChatGPT Business subscription)
    OPENAI_API_KEY: str = ""
    
    # Webhook configuration for ERP integration
    WEBHOOK_ENABLED: bool = False
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None
    
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Static files serving
    SERVE_ADMIN_PORTAL: bool = True
    ADMIN_PORTAL_PATH: str = "./admin-dist"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
