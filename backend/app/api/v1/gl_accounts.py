from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import GLAccount, GLAccountMapping, Category
from app.schemas import (
    GLAccountCreate, GLAccountUpdate, GLAccountResponse,
    GLAccountMappingCreate, GLAccountMappingResponse, GLAccountMappingDetail
)
from app.middleware.auth import get_current_admin_user, get_current_user
from app.services.gl_assign import AssignError, choose_reassignment, expense_account_gl, links_released_by_removal
from app.services.gl_rollup import ParentLinkError, parent_code_for, validate_parent
from pydantic import BaseModel
from typing import List, Optional
from app.schemas import UUID4
import uuid

router = APIRouter(prefix="/gl-accounts", tags=["GL Accounts"])


def parent_map(db: Session) -> dict[str, str | None]:
    rows = db.query(GLAccount.id, GLAccount.parent_id).all()
    return {str(row.id): (str(row.parent_id) if row.parent_id else None) for row in rows}


def place_on_chart(gl_account: GLAccount, known: dict, db: Session) -> None:
    """Set the parent from the code. 6410 lands under 6400, and 6400 stands on its own."""
    parent_code = parent_code_for(gl_account.account_code)
    if parent_code is None:
        gl_account.parent_id = None
        return
    parent = known.get(parent_code)
    if parent is None:
        parent = GLAccount(account_code=parent_code, account_name=parent_code, is_active=True)
        db.add(parent)
        db.flush()
        known[parent_code] = parent
    elif not parent.is_active:
        parent.is_active = True
    gl_account.parent_id = parent.id
    check_parent(gl_account.id, gl_account.parent_id, db)


def check_parent(account_id, parent_id, db: Session) -> None:
    try:
        validate_parent(
            str(account_id),
            str(parent_id) if parent_id else None,
            parent_map(db),
        )
    except ParentLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    db.flush()
    check_parent(db_account.id, db_account.parent_id, db)
    db.commit()
    db.refresh(db_account)
    return db_account


class ExpenseAccountCreate(BaseModel):
    name: str
    description: Optional[str] = None
    gl_code: str
    gl_name: str
    parent_code: Optional[str] = None
    parent_name: Optional[str] = None


class ExpenseAccountOut(BaseModel):
    category_id: UUID4
    name: str
    description: Optional[str] = None
    gl_account_id: Optional[UUID4] = None
    gl_code: Optional[str] = None
    gl_name: Optional[str] = None
    parent_id: Optional[UUID4] = None
    parent_code: Optional[str] = None
    parent_name: Optional[str] = None
    removed_code: Optional[str] = None
    removed_name: Optional[str] = None


class ExpenseAccountAssign(BaseModel):
    gl_account_id: Optional[UUID4] = None
    gl_code: Optional[str] = None
    gl_name: Optional[str] = None


def _account_view(category: Category) -> ExpenseAccountOut:
    mapping = category.gl_mapping
    account = mapping.gl_account if mapping else None
    parent = account.parent if account else None
    shown = expense_account_gl(None if account is None else {
        "id": account.id,
        "code": account.account_code,
        "name": account.account_name,
        "is_active": bool(account.is_active),
        "parent_id": parent.id if parent else None,
        "parent_code": parent.account_code if parent else None,
        "parent_name": parent.account_name if parent else None,
        "parent_active": bool(parent.is_active) if parent else False,
    })
    return ExpenseAccountOut(
        category_id=category.id,
        name=category.name,
        description=category.description,
        **shown,
    )


def align_chart(db: Session) -> None:
    """Point every four-digit account at the parent its code already names."""
    known = {row.account_code: row for row in db.query(GLAccount).all()}
    changed = False
    for account in list(known.values()):
        if not account.is_active:
            continue
        try:
            parent_code = parent_code_for(account.account_code)
        except ParentLinkError:
            continue
        if parent_code is None:
            if account.parent_id is not None:
                account.parent_id = None
                changed = True
            continue
        parent = known.get(parent_code)
        if parent is None:
            parent = GLAccount(account_code=parent_code, account_name=parent_code, is_active=True)
            db.add(parent)
            db.flush()
            known[parent_code] = parent
            changed = True
        elif not parent.is_active:
            parent.is_active = True
            changed = True
        if account.parent_id != parent.id:
            account.parent_id = parent.id
            changed = True
    if changed:
        db.commit()


@router.get("/expense-accounts", response_model=List[ExpenseAccountOut])
def list_expense_accounts(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    align_chart(db)
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.name).all()
    return [_account_view(category) for category in categories]


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

    known = {row.account_code: row for row in db.query(GLAccount).all()}
    try:
        parent_code_for(gl_code)
    except ParentLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    gl_account = known.get(gl_code)
    if gl_account is None:
        gl_account = GLAccount(account_code=gl_code, account_name=gl_name, is_active=True)
        db.add(gl_account)
        db.flush()
        known[gl_code] = gl_account
    else:
        gl_account.is_active = True
        if gl_code.endswith("00") or gl_account.account_name == gl_account.account_code:
            gl_account.account_name = gl_name
    place_on_chart(gl_account, known, db)

    category = Category(name=name, description=body.description, is_active=True)
    db.add(category)
    db.flush()
    mapping = GLAccountMapping(category_id=category.id, gl_account_id=gl_account.id)
    db.add(mapping)
    db.commit()
    db.refresh(category)
    return _account_view(category)


@router.put("/expense-accounts/{category_id}", response_model=ExpenseAccountOut)
def reassign_expense_account(
    category_id: uuid.UUID,
    body: ExpenseAccountAssign,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id, Category.is_active == True).first()
    if not category:
        raise HTTPException(status_code=404, detail="Expense account not found")

    accounts = db.query(GLAccount).all()
    known = [
        {
            "id": str(account.id),
            "code": account.account_code,
            "name": account.account_name,
            "is_active": bool(account.is_active),
        }
        for account in accounts
    ]
    try:
        choice = choose_reassignment(
            str(body.gl_account_id) if body.gl_account_id else None,
            body.gl_code,
            body.gl_name,
            known,
        )
    except AssignError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    by_id = {str(account.id): account for account in accounts}
    by_code = {account.account_code: account for account in accounts}
    if choice["kind"] == "create":
        try:
            parent_code_for(choice["code"])
        except ParentLinkError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        gl_account = GLAccount(account_code=choice["code"], account_name=choice["name"], is_active=True)
        db.add(gl_account)
        db.flush()
        by_code[gl_account.account_code] = gl_account
    else:
        gl_account = by_id[choice["id"]]
        if choice["kind"] == "reactivate":
            gl_account.is_active = True
            if choice.get("name"):
                gl_account.account_name = choice["name"]
    try:
        place_on_chart(gl_account, by_code, db)
    except ParentLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mapping = category.gl_mapping
    if mapping is None:
        mapping = GLAccountMapping(category_id=category.id, gl_account_id=gl_account.id)
        db.add(mapping)
    else:
        mapping.gl_account_id = gl_account.id
    db.commit()
    db.refresh(category)
    return _account_view(category)


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
    if "parent_id" in update_data:
        check_parent(account.id, update_data["parent_id"], db)
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

    grouped: dict[str, list[str]] = {}
    mapping_rows = {str(mapping.id): mapping for mapping in db.query(GLAccountMapping).all()}
    for mapping in mapping_rows.values():
        grouped.setdefault(str(mapping.gl_account_id), []).append(str(mapping.id))
    drop_ids, child_ids = links_released_by_removal(str(account.id), grouped, parent_map(db))
    for mapping_id in drop_ids:
        db.delete(mapping_rows[mapping_id])
    children = {str(row.id): row for row in db.query(GLAccount).all()}
    for child_id in child_ids:
        children[child_id].parent_id = None
    account.is_active = False
    db.commit()
    return None

