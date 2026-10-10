from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.models import Expense, ExpenseReport, ReportStatus, Trip
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
    rows = db.query(Expense).filter(
        Expense.report_id == report.id,
        Expense.removed_at.is_(None),
    ).all()
    report.total_amount = report_total(row.amount for row in rows)
    report.expense_count = len(rows)


def _report_rows(reports: list[ExpenseReport]) -> list[dict]:
    rows = []
    for report in reports:
        status = report.status.value if hasattr(report.status, "value") else report.status
        rows.append({
            "id": str(report.id),
            "title": report.title or "",
            "period_start": report.period_start,
            "period_end": report.period_end,
            "status": status,
        })
    return rows


def place_expense(db: Session, expense: Expense, forced_report_id=None) -> tuple[ExpenseReport, str]:
    """Put a receipt on the open report that covers its date."""
    from app.services.corrections import DestinationError, choose_destination

    reports = db.query(ExpenseReport).filter(ExpenseReport.user_id == expense.user_id).all()
    trip = None
    if expense.trip_id:
        trip_row = db.query(Trip).filter(Trip.id == expense.trip_id).first()
        if trip_row and trip_row.report and trip_row.report.user_id == expense.user_id:
            trip = {"id": str(trip_row.id), "name": trip_row.name, "report_id": str(trip_row.report_id)}
    choice = choose_destination(
        expense.expense_date,
        _report_rows(reports),
        trip,
        str(forced_report_id) if forced_report_id else None,
    )
    if not choice["ok"]:
        raise DestinationError(choice["message"])
    previous_id = expense.report_id
    if choice["creates_report"]:
        start, end = month_bounds(expense.expense_date)
        report = ExpenseReport(
            user_id=expense.user_id,
            period_start=start,
            period_end=end,
            title=choice["title"],
            total_amount=0,
            currency=expense.currency or "USD",
            expense_count=0,
            status=ReportStatus.DRAFT,
        )
        db.add(report)
        db.flush()
    else:
        report = next(item for item in reports if str(item.id) == choice["report_id"])
    expense.report_id = report.id
    expense.trip_id = uuid.UUID(choice["trip_id"]) if choice["trip_id"] else None
    refresh_report(db, report)
    if previous_id and previous_id != report.id:
        previous = db.query(ExpenseReport).filter(ExpenseReport.id == previous_id).first()
        if previous is not None:
            refresh_report(db, previous)
    return report, choice["message"]


def month_bounds(today: date | None = None):
    current = today or date.today()
    start = current.replace(day=1)
    end = start.replace(day=monthrange(start.year, start.month)[1])
    return start, end
