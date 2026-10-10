"""Rules for fixing a receipt or a report after it has been filed."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


class CorrectionError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DestinationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def status_text(status) -> str:
    value = getattr(status, "value", status)
    return str(value or "").lower()


def report_is_open(status) -> bool:
    """A draft or a report sent back can still be changed by the person who owns it."""
    return status_text(status) in {"draft", "rejected"}


def can_withdraw(status) -> bool:
    return status_text(status) == "submitted"


def can_send_back(status) -> bool:
    return status_text(status) in {"submitted", "approved"}


def line_status_for(report_status) -> str:
    """A receipt waits for review only while its report is submitted."""
    key = status_text(report_status)
    if key == "submitted":
        return "pending"
    if key == "approved":
        return "approved"
    return "draft"


def reconcile_line(report_status, line_status: str) -> str | None:
    """The status a receipt should have, when it does not already match its report."""
    wanted = line_status_for(report_status)
    if status_text(line_status) == wanted:
        return None
    return wanted


def _title(report: dict, fallback: date | None = None) -> str:
    name = str(report.get("title") or "").strip()
    if name:
        return name
    start = fallback or report["period_start"]
    return start.strftime("%B %Y")


def _added(title: str, trip_name: str | None = None, dropped_trip: str | None = None, fresh: bool = False) -> str:
    if fresh:
        sentence = f"This receipt will start a new report, {title}."
    elif trip_name:
        sentence = f"This receipt will be added to {title}, on the trip {trip_name}."
    else:
        sentence = f"This receipt will be added to {title}."
    if not dropped_trip:
        return sentence
    return f"The trip {dropped_trip} does not cover this date, so it will not be used. {sentence}"


def choose_destination(expense_date: date, reports: list[dict], trip: dict | None = None, forced_report_id: str | None = None) -> dict:
    """Pick the open report a receipt joins, without creating one."""
    by_id = {str(item["id"]): item for item in reports}

    def fail(message: str) -> dict:
        return {"ok": False, "message": message}

    def succeed(report_id, title: str, creates: bool, trip_id, message: str) -> dict:
        return {
            "ok": True,
            "report_id": report_id,
            "title": title,
            "creates_report": creates,
            "trip_id": trip_id,
            "message": message,
        }

    if forced_report_id:
        chosen = by_id.get(str(forced_report_id))
        if chosen is None:
            return fail("That report could not be used. File this receipt from Home.")
        title = _title(chosen)
        if not report_is_open(chosen["status"]):
            return fail("This report is with your supervisor. Pull it back before adding a receipt.")
        if not (chosen["period_start"] <= expense_date <= chosen["period_end"]):
            return fail(f"That date is outside {title}. Change the date, or file this receipt from Home.")
        if trip and str(trip.get("report_id")) == str(chosen["id"]):
            return succeed(str(chosen["id"]), title, False, str(trip["id"]), _added(title, trip.get("name") or "this trip"))
        dropped = (trip.get("name") or "this trip") if trip else None
        return succeed(str(chosen["id"]), title, False, None, _added(title, dropped_trip=dropped))

    dropped_name = None
    if trip:
        host = by_id.get(str(trip.get("report_id")))
        if host and report_is_open(host["status"]) and host["period_start"] <= expense_date <= host["period_end"]:
            title = _title(host)
            return succeed(str(host["id"]), title, False, str(trip["id"]), _added(title, trip.get("name") or "this trip"))
        dropped_name = trip.get("name") or "this trip"

    open_hits = [
        item for item in reports
        if report_is_open(item["status"]) and item["period_start"] <= expense_date <= item["period_end"]
    ]
    if open_hits:
        chosen = sorted(open_hits, key=lambda item: (item["period_end"] - item["period_start"]).days)[0]
        title = _title(chosen)
        return succeed(str(chosen["id"]), title, False, None, _added(title, dropped_trip=dropped_name))

    title = expense_date.strftime("%B %Y")
    return succeed(None, title, True, None, _added(title, dropped_trip=dropped_name, fresh=True))


def _money(amount) -> Decimal:
    try:
        parsed = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise CorrectionError("Enter the receipt total.") from None
    if parsed <= 0:
        raise CorrectionError("Enter the receipt total.")
    return parsed


def save_line(db, expense, merchant_name: str, amount, expense_date: date, category_id):
    """Correct merchant, total, date, or account on an open report."""
    from app.models import Category, GLAccountMapping
    from app.services.gl_assign import posting_gl_id
    from app.services.merchants import resolve_merchant
    from app.services.reports import place_expense

    if expense.removed_at is not None:
        raise CorrectionError("That receipt was removed.")
    report = expense.report
    if report is None or not report_is_open(report.status):
        raise CorrectionError("This report is with your supervisor. Pull it back, or ask an admin to send it back.")
    merchant_name = " ".join((merchant_name or "").split())
    if not merchant_name:
        raise CorrectionError("Enter the merchant from the receipt.")
    parsed = _money(amount)
    category = db.query(Category).filter(Category.id == category_id, Category.is_active == True).first()
    if category is None:
        raise CorrectionError("Choose an expense account.")
    mapping = db.query(GLAccountMapping).filter(GLAccountMapping.category_id == category.id).first()
    gl_account = mapping.gl_account if mapping else None
    if gl_account is None or not posting_gl_id(str(gl_account.id), bool(gl_account.is_active)):
        raise CorrectionError("This expense account is not assigned to a GL account.")
    origin_id = expense.report_id
    expense.merchant_name = merchant_name
    expense.amount = parsed
    expense.expense_date = expense_date
    expense.category_id = category.id
    expense.gl_account_id = gl_account.id
    expense.category_manually_set = True
    merchant = resolve_merchant(db, merchant_name)
    expense.merchant_id = merchant.id if merchant else None
    stays_here = report.period_start <= expense_date <= report.period_end
    landed, message = place_expense(db, expense, forced_report_id=report.id if stays_here else None)
    if landed.id != origin_id:
        return landed, message
    return landed, "Saved."


def take_line_off(db, expense, when: datetime | None = None):
    """Keep the receipt in the database and drop it from the report total."""
    from app.services.reports import refresh_report

    if expense.removed_at is not None:
        raise CorrectionError("That receipt was removed.")
    report = expense.report
    if report is not None and not report_is_open(report.status):
        raise CorrectionError("This report is with your supervisor. Pull it back, or ask an admin to send it back.")
    expense.removed_at = when or datetime.utcnow()
    if report is not None:
        refresh_report(db, report)
    return report


def stamp_lines(db, report, actor_id=None, now: datetime | None = None) -> None:
    """Make every receipt on a report match that report's status."""
    from app.models import Expense, ExpenseStatus
    from app.services.reports import refresh_report

    moment = now or datetime.utcnow()
    wanted = line_status_for(report.status)
    rows = db.query(Expense).filter(Expense.report_id == report.id, Expense.removed_at.is_(None)).all()
    for row in rows:
        row.status = ExpenseStatus(wanted)
        if wanted == "pending":
            row.submitted_at = row.submitted_at or moment
        elif wanted == "draft":
            row.submitted_at = None
            row.approved_at = None
            row.approved_by = None
        elif wanted == "approved":
            row.approved_at = row.approved_at or moment
            if actor_id is not None and row.approved_by is None:
                row.approved_by = actor_id
    refresh_report(db, report)
