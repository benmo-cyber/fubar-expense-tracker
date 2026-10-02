from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import GLAccount, GLAccountMapping, Category
from app.schemas import (
    GLAccountCreate, GLAccountUpdate, GLAccountResponse,
    GLAccountMappingCreate, GLAccountMappingResponse, GLAccountMappingDetail
)
from app.middleware.auth import get_current_admin_user
from typing import List
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
