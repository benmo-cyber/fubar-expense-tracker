from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.core.database import get_db
from app.models import Expense, ExpenseStatus, ExpenseReport, ReportCategoryBreakdown, Category
from app.schemas import (
    ExpenseExportRequest, ExpenseDetailResponse, DashboardStats
)
from app.middleware.auth import get_current_user, get_current_admin_user
from typing import List
from datetime import date
import csv
import json
import io

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    pending_count = db.query(func.count(Expense.id)).filter(
        Expense.status == ExpenseStatus.PENDING
    ).scalar()
    
    approved_count = db.query(func.count(Expense.id)).filter(
        Expense.status == ExpenseStatus.APPROVED
    ).scalar()
    
    rejected_count = db.query(func.count(Expense.id)).filter(
        Expense.status == ExpenseStatus.REJECTED
    ).scalar()
    
    total_pending_amount = db.query(func.sum(Expense.amount)).filter(
        Expense.status == ExpenseStatus.PENDING
    ).scalar() or 0
    
    total_approved_amount = db.query(func.sum(Expense.amount)).filter(
        Expense.status == ExpenseStatus.APPROVED
    ).scalar() or 0
    
    recent_expenses = db.query(Expense).filter(
        Expense.status == ExpenseStatus.PENDING
    ).order_by(Expense.submitted_at.desc()).limit(10).all()
    
    return DashboardStats(
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        total_pending_amount=total_pending_amount,
        total_approved_amount=total_approved_amount,
        recent_expenses=recent_expenses
    )


@router.post("/export")
def export_expenses(
    export_request: ExpenseExportRequest,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(Expense).filter(
        and_(
            Expense.expense_date >= export_request.start_date,
            Expense.expense_date <= export_request.end_date
        )
    )
    
    if export_request.status:
        query = query.filter(Expense.status == export_request.status)
    
    if export_request.category_id:
        query = query.filter(Expense.category_id == export_request.category_id)
    
    expenses = query.order_by(Expense.expense_date).all()
    
    if export_request.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "ID", "User Email", "Date", "Merchant", "Description", "Amount", "Currency",
            "Category", "GL Account Code", "Status", "Submitted At", "Approved At"
        ])
        
        for expense in expenses:
            writer.writerow([
                str(expense.id),
                expense.user.email if expense.user else "",
                expense.expense_date.isoformat(),
                expense.merchant_name or "",
                expense.description or "",
                float(expense.amount),
                expense.currency,
                expense.category.name if expense.category else "",
                expense.gl_account.account_code if expense.gl_account else "",
                expense.status.value,
                expense.submitted_at.isoformat() if expense.submitted_at else "",
                expense.approved_at.isoformat() if expense.approved_at else ""
            ])
        
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=expenses_{export_request.start_date}_{export_request.end_date}.csv"}
        )
    
    else:
        expense_data = []
        for expense in expenses:
            expense_data.append({
                "id": str(expense.id),
                "user_email": expense.user.email if expense.user else None,
                "date": expense.expense_date.isoformat(),
                "merchant": expense.merchant_name,
                "description": expense.description,
                "amount": float(expense.amount),
                "currency": expense.currency,
                "category": expense.category.name if expense.category else None,
                "gl_account_code": expense.gl_account.account_code if expense.gl_account else None,
                "status": expense.status.value,
                "submitted_at": expense.submitted_at.isoformat() if expense.submitted_at else None,
                "approved_at": expense.approved_at.isoformat() if expense.approved_at else None
            })
        
        return Response(
            content=json.dumps(expense_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=expenses_{export_request.start_date}_{export_request.end_date}.json"}
        )
