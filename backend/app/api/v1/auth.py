import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from datetime import datetime

from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.services.passwords import (
    can_send_reset,
    forgot_message,
    make_reset_token,
    read_reset_token,
    reset_link,
    send_reset_email,
    validate_new_password,
)
from app.models import User
from app.schemas import UserCreate, UserResponse, Token, UserUpdate
from pydantic import BaseModel, EmailStr
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        department=user_data.department,
        default_currency=user_data.default_currency
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "must_change_password": bool(user.must_change_password),
    }


class EmailRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str


class ChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.post("/forgot-password")
def forgot_password(body: EmailRequest, db: Session = Depends(get_db)):
    ready = can_send_reset(settings.EMAIL_HOST_USER, settings.PUBLIC_APP_URL)
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if ready and user is not None:
        issued_at = int(datetime.utcnow().timestamp())
        token = make_reset_token(settings.SECRET_KEY, str(user.id), user.hashed_password, issued_at)
        try:
            send_reset_email(
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                settings.EMAIL_USE_TLS,
                settings.EMAIL_HOST_USER,
                settings.EMAIL_HOST_PASSWORD,
                settings.DEFAULT_FROM_EMAIL,
                user.email,
                reset_link(settings.PUBLIC_APP_URL, token),
            )
        except Exception:
            pass
    return {"message": forgot_message(ready)}


@router.post("/reset-password")
def reset_password(body: ResetRequest, db: Session = Depends(get_db)):
    problem = validate_new_password(body.new_password, body.confirm_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    user_id = (body.token or "").split(".", 1)[0]
    user = None
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    except ValueError:
        user = None
    now = int(datetime.utcnow().timestamp())
    if user is None or read_reset_token(settings.SECRET_KEY, body.token, user.hashed_password, now) != str(user.id):
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")
    user.hashed_password = get_password_hash(body.new_password)
    user.must_change_password = False
    db.commit()
    return {"ok": True}


@router.post("/change-password")
def change_password(
    body: ChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    problem = validate_new_password(body.new_password, body.confirm_password, body.current_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    current_user.hashed_password = get_password_hash(body.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.department is not None:
        current_user.department = user_update.department
    if user_update.default_currency is not None:
        current_user.default_currency = user_update.default_currency
    
    db.commit()
    db.refresh(current_user)
    return current_user
