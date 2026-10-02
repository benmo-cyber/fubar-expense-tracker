from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.core.database import get_db
from app.models import Expense, Category, User, ExpenseStatus, GLAccount, GLAccountMapping
from app.schemas import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseDetailResponse,
    ExpenseApproveRequest, ExpenseRejectRequest, BulkApprovalResponse,
    ReceiptScanResponse, OCRResult, AICategorization
)
from app.middleware.auth import get_current_user, get_current_admin_user
from app.services.storage import storage_service
from app.services.webhook import webhook_service
from app.services.ocr import ocr_service
from app.services.ai import ai_service
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("/scan-receipt", response_model=ReceiptScanResponse)
async def scan_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    image_content = await file.read()
    
    ocr_result = ocr_service.extract_text_from_image(image_content)
    
    ocr_response = OCRResult(
        merchant_name=ocr_result.get("merchant_name"),
        amount=ocr_result.get("amount"),
        date=ocr_result.get("date"),
        confidence=ocr_result["confidence"],
        raw_text=ocr_result["raw_text"]
    )
    
    ai_suggestion = None
    categories = db.query(Category).filter(Category.is_active == True).all()
    
    if categories:
        category_dicts = [
            {"id": cat.id, "name": cat.name, "description": cat.description}
            for cat in categories
        ]
        
        ai_result = ai_service.categorize_expense(
            ocr_text=ocr_result["raw_text"],
            merchant_name=ocr_result.get("merchant_name"),
            amount=ocr_result.get("amount"),
            categories=category_dicts
        )
        
        if ai_result:
            ai_suggestion = AICategorization(**ai_result)
    
    return ReceiptScanResponse(
        ocr_result=ocr_response,
        ai_suggestion=ai_suggestion
    )


@router.post("/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    url = storage_service.upload_file(file.file, file.filename, file.content_type)
    return {"receipt_url": url}


@router.post("", response_model=ExpenseDetailResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    gl_account_id = None
    if expense.category_id:
        mapping = db.query(GLAccountMapping).filter(
            GLAccountMapping.category_id == expense.category_id
        ).first()
        if mapping:
            gl_account_id = mapping.gl_account_id
    
    db_expense = Expense(
        user_id=current_user.id,
        amount=expense.amount,
        currency=expense.currency,
        description=expense.description,
        merchant_name=expense.merchant_name,
        expense_date=expense.expense_date,
        category_id=expense.category_id,
        gl_account_id=gl_account_id,
        receipt_url=expense.receipt_url,
        receipt_ocr_text=expense.receipt_ocr_text,
        ocr_confidence=expense.ocr_confidence,
        ai_suggested_category_id=expense.ai_suggested_category_id,
        ai_confidence=expense.ai_confidence,
        notes=expense.notes,
        location_lat=expense.location_lat,
        location_lng=expense.location_lng,
        status=ExpenseStatus.DRAFT
    )
    
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    
    return db_expense


@router.get("", response_model=List[ExpenseDetailResponse])
def list_expenses(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ExpenseStatus] = None,
    category_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Expense)
    
    if current_user.role != "admin":
        query = query.filter(Expense.user_id == current_user.id)
    
    if status:
        query = query.filter(Expense.status == status)
    
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    
    expenses = query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()
    return expenses


@router.get("/{expense_id}", response_model=ExpenseDetailResponse)
def get_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if current_user.role != "admin" and expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return expense


@router.put("/{expense_id}", response_model=ExpenseDetailResponse)
def update_expense(
    expense_id: uuid.UUID,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if expense.status not in [ExpenseStatus.DRAFT, ExpenseStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Cannot edit submitted/approved expenses")
    
    update_data = expense_update.model_dump(exclude_unset=True)
    
    if "category_id" in update_data and update_data["category_id"]:
        expense.category_manually_set = True
        
        if not expense_update.gl_override:
            mapping = db.query(GLAccountMapping).filter(
                GLAccountMapping.category_id == update_data["category_id"]
            ).first()
            if mapping:
                update_data["gl_account_id"] = mapping.gl_account_id
    
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if expense.status == ExpenseStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Cannot delete approved expenses")
    
    if expense.receipt_url:
        storage_service.delete_file(expense.receipt_url)
    
    db.delete(expense)
    db.commit()
    return None


@router.post("/{expense_id}/submit", response_model=ExpenseDetailResponse)
def submit_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if expense.status != ExpenseStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Expense already submitted")
    
    expense.status = ExpenseStatus.PENDING
    expense.submitted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(expense)
    return expense


@router.post("/approve", response_model=BulkApprovalResponse)
async def approve_expenses(
    request: ExpenseApproveRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    approved_count = 0
    failed_count = 0
    failed_ids = []
    
    for expense_id in request.expense_ids:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        
        if not expense or expense.status != ExpenseStatus.PENDING:
            failed_count += 1
            failed_ids.append(expense_id)
            continue
        
        expense.status = ExpenseStatus.APPROVED
        expense.approved_at = datetime.utcnow()
        expense.approved_by = current_user.id
        approved_count += 1
        
        # Send webhook notification for ERP integration
        await webhook_service.notify_expense_approved({
            "id": str(expense.id),
            "amount": float(expense.amount),
            "currency": expense.currency,
            "expense_date": expense.expense_date.isoformat(),
            "merchant_name": expense.merchant_name,
            "gl_account_code": expense.gl_account.account_code if expense.gl_account else None,
            "employee_email": expense.user.email if expense.user else None,
            "approved_at": expense.approved_at.isoformat(),
            "approved_by": current_user.email
        })
    
    db.commit()
    
    return BulkApprovalResponse(
        approved_count=approved_count,
        failed_count=failed_count,
        failed_ids=failed_ids
    )


@router.post("/reject", response_model=BulkApprovalResponse)
def reject_expenses(
    request: ExpenseRejectRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    approved_count = 0
    failed_count = 0
    failed_ids = []
    
    for expense_id in request.expense_ids:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        
        if not expense or expense.status != ExpenseStatus.PENDING:
            failed_count += 1
            failed_ids.append(expense_id)
            continue
        
        expense.status = ExpenseStatus.REJECTED
        expense.rejection_reason = request.rejection_reason
        approved_count += 1
    
    db.commit()
    
    return BulkApprovalResponse(
        approved_count=approved_count,
        failed_count=failed_count,
        failed_ids=failed_ids
    )
