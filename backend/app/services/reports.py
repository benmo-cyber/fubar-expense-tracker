from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import Expense, ExpenseReport, ReportStatus, Trip


OPEN_FOR_FILING = {ReportStatus.DRAFT, ReportStatus.REJECTED}


def refresh_report(db: Session, report: ExpenseReport) -> None:
    db.flush()
    rows = db.query(Expense).filter(Expense.report_id == report.id).all()
    report.total_amount = sum((row.amount or 0) for row in rows) or Decimal("0")
    report.expense_count = len(rows)


def place_expense(db: Session, expense: Expense) -> ExpenseReport:
    report = None
    if expense.trip_id:
        trip = db.query(Trip).filter(Trip.id == expense.trip_id).first()
        if trip and trip.report and trip.report.user_id == expense.user_id:
            period_fits = trip.report.period_start <= expense.expense_date <= trip.report.period_end
            if period_fits and trip.report.status in OPEN_FOR_FILING:
                report = trip.report
            else:
                expense.trip_id = None
    if report is None:
        candidates = db.query(ExpenseReport).filter(
            ExpenseReport.user_id == expense.user_id,
            ExpenseReport.period_start <= expense.expense_date,
            ExpenseReport.period_end >= expense.expense_date,
            ExpenseReport.status.in_(list(OPEN_FOR_FILING)),
        ).all()
        if candidates:
            report = sorted(candidates, key=lambda item: (item.period_end - item.period_start).days)[0]
    if report is None:
        start = expense.expense_date.replace(day=1)
        end = start.replace(day=monthrange(start.year, start.month)[1])
        report = ExpenseReport(
            user_id=expense.user_id,
            period_start=start,
            period_end=end,
            title=start.strftime("%B %Y"),
            total_amount=0,
            currency=expense.currency or "USD",
            expense_count=0,
            status=ReportStatus.DRAFT,
        )
        db.add(report)
        db.flush()
    expense.report_id = report.id
    refresh_report(db, report)
    return report


def month_bounds(today: date | None = None):
    current = today or date.today()
    start = current.replace(day=1)
    end = start.replace(day=monthrange(start.year, start.month)[1])
    return start, end
