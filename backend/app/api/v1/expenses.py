from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.core.database import get_db
from app.models import (
    Expense, Category, User, ExpenseStatus, GLAccount, GLAccountMapping,
    ExpenseReport, ReportCategoryBreakdown, ReportStatus, UserRole, Trip,
)
from app.schemas import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseDetailResponse,
    ExpenseApproveRequest, ExpenseRejectRequest,
    ReceiptScanResponse, OCRResult, AICategorization, FileExpenseRequest
)
from app.middleware.auth import get_current_user, get_current_admin_user
from app.services.storage import storage_service
from app.services.ocr import ocr_service
from app.services.corrections import (
    CorrectionError,
    DestinationError,
    choose_destination,
    save_line,
    take_line_off,
)
from app.services.merchants import resolve_merchant
from app.services.reports import _report_rows, place_expense
from app.services.ai import ai_service
from app.services.gl_assign import posting_gl_id
from typing import List, Optional
from datetime import datetime, date
from calendar import monthrange
import uuid

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def parse_receipt_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    text = value.strip()
    for fmt in (
        "%m/%d/%Y",
        "%m/%d/%y",
        "%m-%d-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def add_expense_to_report(db: Session, expense: Expense) -> None:
    start = expense.expense_date.replace(day=1)
    end = start.replace(day=monthrange(start.year, start.month)[1])
    report = db.query(ExpenseReport).filter(
        ExpenseReport.user_id == expense.user_id,
        ExpenseReport.period_start == start,
        ExpenseReport.status == ReportStatus.DRAFT,
    ).first()
    if report is None:
        report = ExpenseReport(
            user_id=expense.user_id,
            period_start=start,
            period_end=end,
            total_amount=0,
            currency=expense.currency,
            expense_count=0,
            status=ReportStatus.DRAFT,
        )
        db.add(report)
        db.flush()

    report.total_amount = (report.total_amount or 0) + expense.amount
    report.expense_count = (report.expense_count or 0) + 1

    if not expense.category_id:
        return

    line = db.query(ReportCategoryBreakdown).filter(
        ReportCategoryBreakdown.report_id == report.id,
        ReportCategoryBreakdown.category_id == expense.category_id,
    ).first()
    if line is None:
        db.add(ReportCategoryBreakdown(
            report_id=report.id,
            category_id=expense.category_id,
            amount=expense.amount,
            expense_count=1,
        ))
    else:
        line.amount = line.amount + expense.amount
        line.expense_count = line.expense_count + 1


@router.post("/scan-receipt", response_model=ReceiptScanResponse)
async def scan_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    image_content = await file.read()
    categories = db.query(Category).filter(Category.is_active == True).all()
    category_dicts = [
        {"id": cat.id, "name": cat.name, "description": cat.description}
        for cat in categories
    ]
    vision = ai_service.read_receipt(image_content, category_dicts) if ai_service.enabled else None

    if vision:
        ocr_response = OCRResult(
            merchant_name=vision.get("merchant_name"),
            amount=vision.get("amount"),
            date=parse_receipt_date(vision.get("date")),
            confidence=vision["confidence"],
            raw_text=vision["raw_text"],
        )
        ai_result = vision.get("category")
    else:
        ocr_result = ocr_service.extract_text_from_image(image_content)
        ocr_response = OCRResult(
            merchant_name=ocr_result.get("merchant_name"),
            amount=ocr_result.get("amount"),
            date=parse_receipt_date(ocr_result.get("date")),
            confidence=ocr_result["confidence"],
            raw_text=ocr_result["raw_text"]
        )
        ai_result = ai_service.choose_category(
            ocr_text=ocr_result["raw_text"],
            merchant_name=ocr_result.get("merchant_name"),
            amount=ocr_result.get("amount"),
            categories=category_dicts
        ) if category_dicts else None

    ai_suggestion = None
    if ai_result:
        mapping = db.query(GLAccountMapping).filter(
            GLAccountMapping.category_id == uuid.UUID(str(ai_result["category_id"]))
        ).first()
        if mapping and mapping.gl_account:
            ai_result["gl_account_id"] = str(mapping.gl_account.id)
            ai_result["gl_account_code"] = mapping.gl_account.account_code
            ai_result["gl_account_name"] = mapping.gl_account.account_name
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
    if not (file.content_type or "").startswith("image/"):
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
        gl_account = mapping.gl_account if mapping else None
        if gl_account and posting_gl_id(str(gl_account.id), bool(gl_account.is_active)):
            gl_account_id = gl_account.id
    
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


@router.post("/file", response_model=ExpenseDetailResponse, status_code=status.HTTP_201_CREATED)
def file_expense(
    amount: float = Form(...),
    merchant_name: str = Form(...),
    expense_date: date = Form(...),
    category_id: uuid.UUID = Form(...),
    currency: str = Form("USD"),
    notes: str = Form(""),
    receipt_ocr_text: str = Form(""),
    ocr_confidence: Optional[float] = Form(None),
    ai_confidence: Optional[float] = Form(None),
    trip_id: Optional[uuid.UUID] = Form(None),
    report_id: Optional[uuid.UUID] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id, Category.is_active == True).first()
    if not category:
        raise HTTPException(status_code=404, detail="Expense account not found")

    mapping = db.query(GLAccountMapping).filter(
        GLAccountMapping.category_id == category.id
    ).first()
    gl_account = mapping.gl_account if mapping else None
    gl_account_id = posting_gl_id(
        str(gl_account.id) if gl_account else None,
        bool(gl_account.is_active) if gl_account else False,
    )
    if not gl_account_id:
        raise HTTPException(status_code=400, detail="This expense account is not assigned to a GL account")

    receipt_url = None
    if file is not None and file.filename:
        receipt_url = storage_service.upload_file(
            file.file,
            file.filename,
            file.content_type or "image/jpeg",
        )

    db_expense = Expense(
        user_id=current_user.id,
        amount=amount,
        currency=currency,
        description=notes,
        merchant_name=merchant_name,
        expense_date=expense_date,
        category_id=category.id,
        gl_account_id=gl_account.id,
        receipt_url=receipt_url,
        receipt_ocr_text=receipt_ocr_text or None,
        ocr_confidence=ocr_confidence,
        ai_suggested_category_id=category.id,
        ai_confidence=ai_confidence,
        notes=notes,
        status=ExpenseStatus.DRAFT,
        category_manually_set=False,
        gl_override=False,
        trip_id=trip_id,
    )
    merchant = resolve_merchant(db, merchant_name)
    if merchant:
        db_expense.merchant_id = merchant.id
    db.add(db_expense)
    db.flush()
    try:
        place_expense(db, db_expense, forced_report_id=report_id)
    except DestinationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=exc.message) from exc
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
    query = db.query(Expense).filter(Expense.removed_at.is_(None))
    
    if current_user.role != "admin":
        query = query.filter(Expense.user_id == current_user.id)
    
    if status:
        query = query.filter(Expense.status == status)
    
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    
    expenses = query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit).all()
    return expenses


def _actor_is_admin(user: User) -> bool:
    role = user.role.value if hasattr(user.role, "value") else user.role
    return role == UserRole.ADMIN or role == "admin" or bool(user.is_superuser)


def _report_payload(report, db: Session):
    from app.api.v1.workspace import report_dict
    return report_dict(report, db)


@router.get("/destination")
def filing_destination(
    expense_date: date,
    trip_id: Optional[uuid.UUID] = None,
    report_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = db.query(ExpenseReport).filter(ExpenseReport.user_id == current_user.id).all()
    trip = None
    if trip_id is not None:
        trip_row = db.query(Trip).filter(Trip.id == trip_id).first()
        if trip_row and trip_row.report and trip_row.report.user_id == current_user.id:
            trip = {"id": str(trip_row.id), "name": trip_row.name, "report_id": str(trip_row.report_id)}
    return choose_destination(
        expense_date,
        _report_rows(reports),
        trip,
        str(report_id) if report_id else None,
    )


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


@router.put("/{expense_id}")
def update_expense(
    expense_id: uuid.UUID,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense or expense.removed_at is not None:
        raise HTTPException(status_code=404, detail="Expense not found")
    if not _actor_is_admin(current_user) and expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = expense_update.model_dump(exclude_unset=True)
    merchant_name = update_data.get("merchant_name", expense.merchant_name)
    amount = update_data.get("amount", expense.amount)
    expense_date = update_data.get("expense_date", expense.expense_date)
    category_id = update_data.get("category_id", expense.category_id)
    if category_id is None:
        raise HTTPException(status_code=400, detail="Choose an expense account.")
    origin_id = expense.report_id
    try:
        landed, message = save_line(db, expense, merchant_name or "", amount, expense_date, category_id)
    except CorrectionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=exc.message) from exc
    if "notes" in update_data:
        expense.notes = update_data["notes"]
    shown = landed
    if origin_id and landed.id != origin_id:
        shown = db.query(ExpenseReport).filter(ExpenseReport.id == origin_id).first() or landed
    db.commit()
    return {"message": message, "report": _report_payload(shown, db)}


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense or expense.removed_at is not None:
        raise HTTPException(status_code=404, detail="Expense not found")
    if not _actor_is_admin(current_user) and expense.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        report = take_line_off(db, expense)
    except CorrectionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=exc.message) from exc
    db.commit()
    return {
        "message": "Removed from the report.",
        "report": _report_payload(report, db) if report is not None else None,
    }


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

    if expense.merchant_name and expense.merchant_id is None:
        merchant = resolve_merchant(db, expense.merchant_name)
        if merchant:
            expense.merchant_id = merchant.id
    place_expense(db, expense)

    db.commit()
    db.refresh(expense)
    return expense


@router.post("/approve")
async def approve_expenses(
    request: ExpenseApproveRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    raise HTTPException(
        status_code=400,
        detail="Approve the report. Individual receipts are not approved on their own.",
    )


@router.post("/reject")
def reject_expenses(
    request: ExpenseRejectRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    raise HTTPException(
        status_code=400,
        detail="Send the report back. Individual receipts are not rejected on their own.",
    )
