from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import GLAccount, GLAccountMapping, Category
from app.schemas import (
    GLAccountCreate, GLAccountUpdate, GLAccountResponse,
    GLAccountMappingCreate, GLAccountMappingResponse, GLAccountMappingDetail
)
from app.middleware.auth import get_current_admin_user, get_current_user
from pydantic import BaseModel
from typing import List, Optional
from app.schemas import UUID4
import uuid

router = APIRouter(prefix="/gl-accounts", tags=["GL Accounts"])


@router.get("", response_model=List[GLAccountResponse])
def list_gl_accounts(
    include_inactive: bool = False,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(GLAccount)
    if not include_inactive:
        query = query.filter(GLAccount.is_active == True)
    accounts = query.order_by(GLAccount.account_code).all()
    return accounts


@router.post("", response_model=GLAccountResponse, status_code=status.HTTP_201_CREATED)
def create_gl_account(
    account: GLAccountCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    existing = db.query(GLAccount).filter(GLAccount.account_code == account.account_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="GL Account with this code already exists")
    
    db_account = GLAccount(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


class ExpenseAccountCreate(BaseModel):
    name: str
    description: Optional[str] = None
    gl_code: str
    gl_name: str


class ExpenseAccountOut(BaseModel):
    category_id: UUID4
    name: str
    description: Optional[str] = None
    gl_account_id: Optional[UUID4] = None
    gl_code: Optional[str] = None
    gl_name: Optional[str] = None


@router.get("/expense-accounts", response_model=List[ExpenseAccountOut])
def list_expense_accounts(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.name).all()
    results = []
    for category in categories:
        mapping = category.gl_mapping
        account = mapping.gl_account if mapping else None
        results.append(ExpenseAccountOut(
            category_id=category.id,
            name=category.name,
            description=category.description,
            gl_account_id=account.id if account else None,
            gl_code=account.account_code if account else None,
            gl_name=account.account_name if account else None,
        ))
    return results


@router.post("/expense-accounts", response_model=ExpenseAccountOut, status_code=status.HTTP_201_CREATED)
def create_expense_account(
    body: ExpenseAccountCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    name = body.name.strip()
    gl_code = body.gl_code.strip()
    gl_name = body.gl_name.strip()
    if not name or not gl_code or not gl_name:
        raise HTTPException(status_code=400, detail="Name, GL code, and GL name are required")

    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="An expense account with this name already exists")

    gl_account = db.query(GLAccount).filter(GLAccount.account_code == gl_code).first()
    if gl_account is None:
        gl_account = GLAccount(account_code=gl_code, account_name=gl_name, is_active=True)
        db.add(gl_account)
        db.flush()
    elif not gl_account.is_active:
        gl_account.is_active = True
        gl_account.account_name = gl_name

    category = Category(name=name, description=body.description, is_active=True)
    db.add(category)
    db.flush()
    mapping = GLAccountMapping(category_id=category.id, gl_account_id=gl_account.id)
    db.add(mapping)
    db.commit()
    db.refresh(category)
    db.refresh(gl_account)
    return ExpenseAccountOut(
        category_id=category.id,
        name=category.name,
        description=category.description,
        gl_account_id=gl_account.id,
        gl_code=gl_account.account_code,
        gl_name=gl_account.account_name,
    )


@router.get("/mappings", response_model=List[GLAccountMappingDetail])
def list_gl_account_mappings(
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    mappings = db.query(GLAccountMapping).all()
    return mappings


@router.post("/mappings", response_model=GLAccountMappingDetail, status_code=status.HTTP_201_CREATED)
def create_gl_account_mapping(
    mapping: GLAccountMappingCreate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == mapping.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    account = db.query(GLAccount).filter(GLAccount.id == mapping.gl_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="GL Account not found")
    
    existing = db.query(GLAccountMapping).filter(
        GLAccountMapping.category_id == mapping.category_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mapping for this category already exists")
    
    db_mapping = GLAccountMapping(**mapping.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


@router.put("/mappings/{mapping_id}", response_model=GLAccountMappingDetail)
def update_gl_account_mapping(
    mapping_id: uuid.UUID,
    gl_account_id: uuid.UUID,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    mapping = db.query(GLAccountMapping).filter(GLAccountMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    account = db.query(GLAccount).filter(GLAccount.id == gl_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="GL Account not found")
    
    mapping.gl_account_id = gl_account_id
    db.commit()
    db.refresh(mapping)
    return mapping


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gl_account_mapping(
    mapping_id: uuid.UUID,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    mapping = db.query(GLAccountMapping).filter(GLAccountMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    db.delete(mapping)
    db.commit()
    return None


@router.get("/{account_id}", response_model=GLAccountResponse)
def get_gl_account(
    account_id: uuid.UUID,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    account = db.query(GLAccount).filter(GLAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="GL Account not found")
    return account


@router.put("/{account_id}", response_model=GLAccountResponse)
def update_gl_account(
    account_id: uuid.UUID,
    account_update: GLAccountUpdate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    account = db.query(GLAccount).filter(GLAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="GL Account not found")
    
    update_data = account_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gl_account(
    account_id: uuid.UUID,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    account = db.query(GLAccount).filter(GLAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="GL Account not found")
    
    account.is_active = False
    db.commit()
    return None

