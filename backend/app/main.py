from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.core.config import settings
from app.api.v1 import auth, expenses, categories, gl_accounts, admin, export, workspace

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
app.include_router(workspace.router, prefix=settings.API_V1_STR)

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
    from app.core.schema_upgrade import ensure_schema
    from app.core.security import get_password_hash
    from app.models import Expense, User, UserRole
    from app.services.merchants import resolve_merchant
    from app.services.reports import place_expense

    ensure_schema()
    db = SessionLocal()
    try:
        from app.core.bootstrap import planned_users

        roles = {"admin": UserRole.ADMIN, "operations": UserRole.OPERATIONS}
        for person in planned_users(
            settings.ENVIRONMENT,
            db.query(User).first() is not None,
            settings.FIRST_ADMIN_EMAIL,
            settings.FIRST_ADMIN_PASSWORD,
            settings.FIRST_ADMIN_NAME,
        ):
            db.add(User(
                email=person["email"],
                hashed_password=get_password_hash(person["password"]),
                full_name=person["full_name"],
                role=roles[person["role"]],
                is_active=True,
                is_superuser=person["role"] == "admin",
            ))
        db.commit()
        admin_user = db.query(User).filter(User.is_superuser.is_(True)).first()
        if admin_user is None:
            admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        if admin_user and not admin_user.is_superuser:
            admin_user.is_superuser = True
        if admin_user:
            for person in db.query(User).filter(User.id != admin_user.id, User.supervisor_id.is_(None)).all():
                person.supervisor_id = admin_user.id
        for expense in db.query(Expense).filter(Expense.report_id.is_(None), Expense.removed_at.is_(None)).all():
            if expense.merchant_name and expense.merchant_id is None:
                merchant = resolve_merchant(db, expense.merchant_name)
                if merchant:
                    expense.merchant_id = merchant.id
            place_expense(db, expense)
        from app.models import ExpenseStatus
        from app.services.corrections import reconcile_line

        for expense in db.query(Expense).filter(Expense.report_id.isnot(None), Expense.removed_at.is_(None)).all():
            if expense.report is None:
                continue
            wanted = reconcile_line(expense.report.status, expense.status)
            if wanted is None:
                continue
            expense.status = ExpenseStatus(wanted)
            if wanted == "draft":
                expense.submitted_at = None
                expense.approved_at = None
                expense.approved_by = None
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
