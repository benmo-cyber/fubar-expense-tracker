from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import Expense, ExpenseReport, ReportStatus, Trip


OPEN_FOR_FILING = {ReportStatus.DRAFT, ReportStatus.REJECTED}
OPEN_TO_SUPERVISOR = {"draft", "submitted", "rejected"}


def team_member_ids(viewer_id: str, people: list[dict]) -> set[str]:
    """Everyone who reports up to this person, through the whole chart."""
    children: dict[str, list[str]] = {}
    for person in people:
        person_id = person.get("id")
        supervisor_id = person.get("supervisor_id")
        if not person_id or not supervisor_id or supervisor_id == person_id:
            continue
        children.setdefault(supervisor_id, []).append(person_id)
    found: set[str] = set()
    stack = list(children.get(viewer_id, []))
    while stack:
        current = stack.pop()
        if current in found or current == viewer_id:
            continue
        found.add(current)
        stack.extend(children.get(current, []))
    return found


def can_view_report(viewer_id: str, is_admin: bool, owner_id: str, status: str, people: list[dict]) -> bool:
    """A supervisor can open an unfinished report filed by someone under them."""
    if is_admin or viewer_id == owner_id:
        return True
    if owner_id not in team_member_ids(viewer_id, people):
        return False
    return (status or "").lower() in OPEN_TO_SUPERVISOR


def report_total(amounts) -> Decimal:
    """Add receipt amounts that may arrive as decimals or plain numbers."""
    total = Decimal("0")
    for amount in amounts:
        if amount is None:
            continue
        total += Decimal(str(amount))
    return total.quantize(Decimal("0.01"))


def refresh_report(db: Session, report: ExpenseReport) -> None:
    db.flush()
    rows = db.query(Expense).filter(Expense.report_id == report.id).all()
    report.total_amount = report_total(row.amount for row in rows)
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
