from sqlalchemy import Column, String, DateTime, Boolean, Text, Numeric, Date, ForeignKey, Integer, Enum as SQLEnum, JSON, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    OPERATIONS = "operations"
    SALES = "sales"
    ADMIN = "admin"


class ExpenseStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    APPROVED = "approved"
    FINALIZED = "finalized"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.OPERATIONS)
    department = Column(String(100))
    default_currency = Column(String(3), default="USD")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    supervisor_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    expenses = relationship("Expense", back_populates="user", foreign_keys="Expense.user_id")
    approved_expenses = relationship("Expense", back_populates="approver", foreign_keys="Expense.approved_by")
    expense_reports = relationship("ExpenseReport", back_populates="user", foreign_keys="ExpenseReport.user_id")
    audit_logs = relationship("AuditLog", back_populates="user")
    supervisor = relationship("User", remote_side=[id], foreign_keys=[supervisor_id])


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    color = Column(String(7))
    icon = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    expenses = relationship("Expense", back_populates="category", foreign_keys="Expense.category_id")
    ai_suggested_expenses = relationship("Expense", back_populates="ai_suggested_category", foreign_keys="Expense.ai_suggested_category_id")
    gl_mapping = relationship("GLAccountMapping", back_populates="category", uselist=False)
    report_breakdowns = relationship("ReportCategoryBreakdown", back_populates="category")


class GLAccount(Base):
    __tablename__ = "gl_accounts"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_code = Column(String(50), nullable=False, unique=True, index=True)
    account_name = Column(String(255), nullable=False)
    description = Column(Text)
    account_type = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    mappings = relationship("GLAccountMapping", back_populates="gl_account")
    expenses = relationship("Expense", back_populates="gl_account")


class GLAccountMapping(Base):
    __tablename__ = "gl_account_mappings"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(Uuid(as_uuid=True), ForeignKey("categories.id"), nullable=False, unique=True)
    gl_account_id = Column(Uuid(as_uuid=True), ForeignKey("gl_accounts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    category = relationship("Category", back_populates="gl_mapping")
    gl_account = relationship("GLAccount", back_populates="mappings")


class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Uuid(as_uuid=True), ForeignKey("categories.id"))
    gl_account_id = Column(Uuid(as_uuid=True), ForeignKey("gl_accounts.id"))
    
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    description = Column(Text)
    merchant_name = Column(String(255))
    expense_date = Column(Date, nullable=False, index=True)
    
    receipt_url = Column(String(500))
    receipt_ocr_text = Column(Text)
    ocr_confidence = Column(Numeric(3, 2))
    
    ai_suggested_category_id = Column(Uuid(as_uuid=True), ForeignKey("categories.id"))
    ai_confidence = Column(Numeric(3, 2))
    category_manually_set = Column(Boolean, default=False)
    
    status = Column(SQLEnum(ExpenseStatus), nullable=False, default=ExpenseStatus.DRAFT, index=True)
    notes = Column(Text)
    rejection_reason = Column(Text)
    location_lat = Column(Numeric(10, 8))
    location_lng = Column(Numeric(11, 8))
    
    gl_override = Column(Boolean, default=False)
    merchant_id = Column(Uuid(as_uuid=True), ForeignKey("merchants.id"))
    report_id = Column(Uuid(as_uuid=True), ForeignKey("expense_reports.id"))
    trip_id = Column(Uuid(as_uuid=True), ForeignKey("trips.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    approved_by = Column(Uuid(as_uuid=True), ForeignKey("users.id"))
    
    user = relationship("User", back_populates="expenses", foreign_keys=[user_id])
    approver = relationship("User", back_populates="approved_expenses", foreign_keys=[approved_by])
    category = relationship("Category", back_populates="expenses", foreign_keys=[category_id])
    ai_suggested_category = relationship("Category", back_populates="ai_suggested_expenses", foreign_keys=[ai_suggested_category_id])
    gl_account = relationship("GLAccount", back_populates="expenses")
    merchant = relationship("Merchant", back_populates="expenses")
    report = relationship("ExpenseReport", back_populates="expenses")
    trip = relationship("Trip", back_populates="expenses")


class ExpenseReport(Base):
    __tablename__ = "expense_reports"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    total_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    expense_count = Column(Integer, nullable=False)
    
    report_pdf_url = Column(String(500))
    report_csv_url = Column(String(500))
    screenshot_url = Column(String(500))
    title = Column(String(255))
    review_notes = Column(Text)
    reviewed_by = Column(Uuid(as_uuid=True), ForeignKey("users.id"))
    status = Column(SQLEnum(ReportStatus), nullable=False, default=ReportStatus.DRAFT)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finalized_at = Column(DateTime)
    submitted_at = Column(DateTime)
    
    user = relationship("User", back_populates="expense_reports", foreign_keys=[user_id])
    expenses = relationship("Expense", back_populates="report")
    trips = relationship("Trip", back_populates="report", cascade="all, delete-orphan")
    category_breakdowns = relationship("ReportCategoryBreakdown", back_populates="report", cascade="all, delete-orphan")


class ReportCategoryBreakdown(Base):
    __tablename__ = "report_category_breakdown"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(Uuid(as_uuid=True), ForeignKey("expense_reports.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Uuid(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    
    amount = Column(Numeric(12, 2), nullable=False)
    expense_count = Column(Integer, nullable=False)
    
    report = relationship("ExpenseReport", back_populates="category_breakdowns")
    category = relationship("Category", back_populates="report_breakdowns")


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    aliases = relationship("MerchantAlias", back_populates="merchant", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="merchant")


class MerchantAlias(Base):
    __tablename__ = "merchant_aliases"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(Uuid(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String(255), nullable=False, unique=True)

    merchant = relationship("Merchant", back_populates="aliases")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(Uuid(as_uuid=True), ForeignKey("expense_reports.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("ExpenseReport", back_populates="trips")
    expenses = relationship("Expense", back_populates="trip")


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    report_id = Column(Uuid(as_uuid=True), ForeignKey("expense_reports.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    read_at = Column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    changes = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user = relationship("User", back_populates="audit_logs")
