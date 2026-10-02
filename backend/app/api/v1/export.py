from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.core.database import get_db
from app.models import Expense, ExpenseStatus
from app.middleware.auth import get_current_user
from typing import Optional, List
from datetime import date
import csv
import json
import io

router = APIRouter(prefix="/expenses", tags=["Export"])


def serialize_expense_for_erp(expense: Expense) -> dict:
    """Serialize expense in Django ERP-friendly format"""
    return {
        "id": str(expense.id),
        "expense_date": expense.expense_date.isoformat(),
        "merchant_name": expense.merchant_name or "",
        "description": expense.description or "",
        "amount": float(expense.amount),
        "currency": expense.currency,
        "category_id": str(expense.category_id) if expense.category_id else None,
        "category_name": expense.category.name if expense.category else None,
        "gl_account_code": expense.gl_account.account_code if expense.gl_account else None,
        "gl_account_name": expense.gl_account.account_name if expense.gl_account else None,
        "gl_account_id": str(expense.gl_account_id) if expense.gl_account_id else None,
        "employee_id": str(expense.user_id),
        "employee_name": expense.user.full_name if expense.user else "",
        "employee_email": expense.user.email if expense.user else "",
        "receipt_url": expense.receipt_url or "",
        "status": expense.status.value,
        "notes": expense.notes or "",
        "submitted_at": expense.submitted_at.isoformat() if expense.submitted_at else None,
        "approved_at": expense.approved_at.isoformat() if expense.approved_at else None,
        "approved_by_id": str(expense.approved_by) if expense.approved_by else None,
        "approved_by_name": expense.approver.full_name if expense.approver else None,
        "created_at": expense.created_at.isoformat(),
        "updated_at": expense.updated_at.isoformat(),
    }


@router.get("/export")
def export_expenses(
    format: str = "json",
    status: Optional[str] = "approved",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Export expenses in Django ERP-friendly format.
    
    Query Parameters:
    - format: json or csv (default: json)
    - status: filter by status (default: approved)
    - start_date: filter expenses from this date
    - end_date: filter expenses until this date
    - category_id: filter by category UUID
    
    Returns expenses with all fields needed for ERP import including GL account codes.
    """
    query = db.query(Expense)
    
    if status:
        try:
            status_enum = ExpenseStatus(status)
            query = query.filter(Expense.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    
    expenses = query.order_by(Expense.expense_date).all()
    
    expense_data = [serialize_expense_for_erp(expense) for expense in expenses]
    
    if format.lower() == "csv":
        output = io.StringIO()
        if expense_data:
            writer = csv.DictWriter(output, fieldnames=expense_data[0].keys())
            writer.writeheader()
            writer.writerows(expense_data)
        
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=expenses_export.csv"
            }
        )
    
    else:
        return {
            "count": len(expense_data),
            "expenses": expense_data
        }


@router.get("/export/{expense_id}")
def export_single_expense(
    expense_id: str,
    db: Session = Depends(get_db)
):
    """
    Export a single expense in Django ERP-friendly format.
    
    Returns complete expense data including GL account mapping.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return serialize_expense_for_erp(expense)


@router.get("/export/batch")
def export_batch_by_ids(
    expense_ids: str,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """
    Export specific expenses by IDs.
    
    Query Parameters:
    - expense_ids: comma-separated list of expense UUIDs
    - format: json or csv (default: json)
    
    Example: /api/v1/expenses/export/batch?expense_ids=uuid1,uuid2,uuid3
    """
    ids = [id.strip() for id in expense_ids.split(",")]
    
    expenses = db.query(Expense).filter(Expense.id.in_(ids)).all()
    
    if not expenses:
        raise HTTPException(status_code=404, detail="No expenses found")
    
    expense_data = [serialize_expense_for_erp(expense) for expense in expenses]
    
    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=expense_data[0].keys())
        writer.writeheader()
        writer.writerows(expense_data)
        
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=expenses_batch.csv"
            }
        )
    
    return {
        "count": len(expense_data),
        "expenses": expense_data
    }
