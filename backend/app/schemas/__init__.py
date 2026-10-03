from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional, List
from datetime import datetime, date
import datetime as dt
from decimal import Decimal
from enum import Enum


class UserRole(str, Enum):
    OPERATIONS = "operations"
    SALES = "sales"
    ADMIN = "admin"


class ExpenseStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[UUID4] = None
    exp: Optional[int] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.OPERATIONS
    department: Optional[str] = None
    default_currency: str = "USD"


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    default_currency: Optional[str] = None


class UserResponse(UserBase):
    id: UUID4
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: UUID4
    created_at: datetime
    
    class Config:
        from_attributes = True


class GLAccountBase(BaseModel):
    account_code: str
    account_name: str
    description: Optional[str] = None
    account_type: Optional[str] = None
    is_active: bool = True


class GLAccountCreate(GLAccountBase):
    pass


class GLAccountUpdate(BaseModel):
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    description: Optional[str] = None
    account_type: Optional[str] = None
    is_active: Optional[bool] = None


class GLAccountResponse(GLAccountBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GLAccountMappingBase(BaseModel):
    category_id: UUID4
    gl_account_id: UUID4


class GLAccountMappingCreate(GLAccountMappingBase):
    pass


class GLAccountMappingResponse(GLAccountMappingBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GLAccountMappingDetail(GLAccountMappingResponse):
    category: CategoryResponse
    gl_account: GLAccountResponse


class ExpenseBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    description: Optional[str] = None
    merchant_name: Optional[str] = None
    expense_date: date
    category_id: Optional[UUID4] = None
    notes: Optional[str] = None
    location_lat: Optional[Decimal] = None
    location_lng: Optional[Decimal] = None


class ExpenseCreate(ExpenseBase):
    receipt_url: Optional[str] = None
    receipt_ocr_text: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    ai_suggested_category_id: Optional[UUID4] = None
    ai_confidence: Optional[Decimal] = None


class FileExpenseRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    merchant_name: str
    expense_date: date
    category_id: UUID4
    notes: Optional[str] = None
    receipt_ocr_text: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    ai_confidence: Optional[Decimal] = None


class ExpenseUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    merchant_name: Optional[str] = None
    expense_date: Optional[date] = None
    category_id: Optional[UUID4] = None
    notes: Optional[str] = None
    gl_account_id: Optional[UUID4] = None
    gl_override: Optional[bool] = None


class ExpenseResponse(ExpenseBase):
    id: UUID4
    user_id: UUID4
    status: ExpenseStatus
    receipt_url: Optional[str] = None
    receipt_ocr_text: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    ai_suggested_category_id: Optional[UUID4] = None
    ai_confidence: Optional[Decimal] = None
    category_manually_set: bool
    gl_account_id: Optional[UUID4] = None
    gl_override: bool
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[UUID4] = None
    
    class Config:
        from_attributes = True


class ExpenseDetailResponse(ExpenseResponse):
    user: UserResponse
    category: Optional[CategoryResponse] = None
    ai_suggested_category: Optional[CategoryResponse] = None
    gl_account: Optional[GLAccountResponse] = None
    approver: Optional[UserResponse] = None


class ExpenseApproveRequest(BaseModel):
    expense_ids: List[UUID4]


class ExpenseRejectRequest(BaseModel):
    expense_ids: List[UUID4]
    rejection_reason: str


class OCRResult(BaseModel):
    merchant_name: Optional[str] = None
    amount: Optional[Decimal] = None
    date: Optional[dt.date] = None
    confidence: Decimal
    raw_text: str


class AICategorization(BaseModel):
    category_id: UUID4
    category_name: str
    confidence: Decimal
    reasoning: str
    gl_account_id: Optional[UUID4] = None
    gl_account_code: Optional[str] = None
    gl_account_name: Optional[str] = None


class ReceiptScanResponse(BaseModel):
    ocr_result: OCRResult
    ai_suggestion: Optional[AICategorization] = None


class ReportCategoryBreakdownResponse(BaseModel):
    category_id: UUID4
    category_name: str
    amount: Decimal
    expense_count: int
    
    class Config:
        from_attributes = True


class ExpenseReportResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    period_start: date
    period_end: date
    total_amount: Decimal
    currency: str
    expense_count: int
    report_pdf_url: Optional[str] = None
    report_csv_url: Optional[str] = None
    status: ReportStatus
    created_at: datetime
    finalized_at: Optional[datetime] = None
    category_breakdowns: List[ReportCategoryBreakdownResponse] = []
    
    class Config:
        from_attributes = True


class ExpenseExportRequest(BaseModel):
    start_date: date
    end_date: date
    status: Optional[ExpenseStatus] = None
    category_id: Optional[UUID4] = None
    format: str = Field(..., pattern="^(csv|json)$")


class DashboardStats(BaseModel):
    pending_count: int
    approved_count: int
    rejected_count: int
    total_pending_amount: Decimal
    total_approved_amount: Decimal
    recent_expenses: List[ExpenseDetailResponse]


class BulkApprovalResponse(BaseModel):
    approved_count: int
    failed_count: int
    failed_ids: List[UUID4] = []
