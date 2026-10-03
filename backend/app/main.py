from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.config import settings
from app.api.v1 import auth, expenses, categories, gl_accounts, admin, export

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(expenses.router, prefix=settings.API_V1_STR)
app.include_router(export.router, prefix=settings.API_V1_STR)
app.include_router(categories.router, prefix=settings.API_V1_STR)
app.include_router(gl_accounts.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

# Serve receipt uploads from local filesystem
if not settings.USE_S3_STORAGE:
    upload_path = Path(settings.LOCAL_STORAGE_PATH)
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_path.parent)), name="uploads")

# Serve admin portal static files if enabled
if settings.SERVE_ADMIN_PORTAL:
    admin_path = Path(settings.ADMIN_PORTAL_PATH)
    if admin_path.exists():
        app.mount("/assets", StaticFiles(directory=str(admin_path / "assets")), name="assets")
        
        @app.get("/admin/{full_path:path}")
        async def serve_admin(full_path: str):
            file_path = admin_path / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(admin_path / "index.html")


@app.on_event("startup")
def seed_local_users():
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash
    from app.models import User, UserRole

    db = SessionLocal()
    try:
        if db.query(User).first():
            return
        db.add(User(
            email="admin@example.com",
            hashed_password=get_password_hash("AdminPass1"),
            full_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
        ))
        db.add(User(
            email="field@example.com",
            hashed_password=get_password_hash("FieldPass1"),
            full_name="Field User",
            role=UserRole.OPERATIONS,
            is_active=True,
        ))
        db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "Expense Tracker API",
        "version": settings.VERSION,
        "docs": "/docs",
        "admin_portal": "/admin" if settings.SERVE_ADMIN_PORTAL else None
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
