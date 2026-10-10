import unittest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    Category,
    Expense,
    ExpenseReport,
    ExpenseStatus,
    GLAccount,
    GLAccountMapping,
    ReportStatus,
    User,
    UserRole,
)
from app.services.corrections import (
    can_send_back,
    can_withdraw,
    choose_destination,
    line_status_for,
    reconcile_line,
    report_is_open,
    save_line,
    stamp_lines,
    take_line_off,
)
from app.services.reports import place_expense


OCTOBER = {
    "id": "oct",
    "title": "October 2026",
    "period_start": date(2026, 10, 1),
    "period_end": date(2026, 10, 31),
    "status": "draft",
}
WEEK = {
    "id": "week",
    "title": "Dallas",
    "period_start": date(2026, 10, 1),
    "period_end": date(2026, 10, 5),
    "status": "draft",
}


class DestinationTests(unittest.TestCase):
    def test_a_receipt_names_the_open_report_it_will_join(self):
        choice = choose_destination(date(2026, 10, 2), [OCTOBER])
        self.assertTrue(choice["ok"])
        self.assertEqual(choice["report_id"], "oct")
        self.assertIn("October 2026", choice["message"])
        self.assertFalse(choice["creates_report"])

    def test_a_date_with_no_open_report_starts_a_new_month(self):
        choice = choose_destination(date(2026, 11, 2), [OCTOBER])
        self.assertTrue(choice["ok"])
        self.assertTrue(choice["creates_report"])
        self.assertEqual(choice["title"], "November 2026")
        self.assertIn("start a new report", choice["message"])

    def test_the_tighter_report_wins_when_two_cover_the_date(self):
        choice = choose_destination(date(2026, 10, 3), [OCTOBER, WEEK])
        self.assertEqual(choice["report_id"], "week")

    def test_a_trip_is_kept_only_when_its_report_covers_the_date(self):
        trip = {"id": "dallas", "name": "Dallas", "report_id": "week"}
        kept = choose_destination(date(2026, 10, 3), [OCTOBER, WEEK], trip)
        self.assertEqual(kept["trip_id"], "dallas")
        self.assertIn("Dallas", kept["message"])
        dropped = choose_destination(date(2026, 10, 20), [OCTOBER, WEEK], trip)
        self.assertIsNone(dropped["trip_id"])
        self.assertIn("does not cover this date", dropped["message"])
        self.assertEqual(dropped["report_id"], "oct")

    def test_filing_onto_a_report_rejects_a_date_outside_it(self):
        choice = choose_destination(date(2026, 11, 2), [OCTOBER], forced_report_id="oct")
        self.assertFalse(choice["ok"])
        self.assertIn("outside October 2026", choice["message"])

    def test_filing_onto_a_submitted_report_is_refused(self):
        closed = {**OCTOBER, "status": "submitted"}
        choice = choose_destination(date(2026, 10, 2), [closed], forced_report_id="oct")
        self.assertFalse(choice["ok"])
        self.assertIn("Pull it back", choice["message"])


class ReportPhaseTests(unittest.TestCase):
    def test_lines_can_change_only_while_the_report_is_open(self):
        self.assertTrue(report_is_open("draft"))
        self.assertTrue(report_is_open("rejected"))
        self.assertFalse(report_is_open("submitted"))
        self.assertFalse(report_is_open("approved"))

    def test_a_submitted_report_can_be_pulled_back_until_it_is_approved(self):
        self.assertTrue(can_withdraw("submitted"))
        self.assertFalse(can_withdraw("draft"))
        self.assertFalse(can_withdraw("approved"))
        self.assertTrue(can_send_back("submitted"))
        self.assertTrue(can_send_back("approved"))
        self.assertFalse(can_send_back("draft"))

    def test_a_receipt_waits_for_review_only_while_its_report_is_submitted(self):
        self.assertEqual(line_status_for("draft"), "draft")
        self.assertEqual(line_status_for("rejected"), "draft")
        self.assertEqual(line_status_for("submitted"), "pending")
        self.assertEqual(line_status_for("approved"), "approved")
        self.assertEqual(reconcile_line("draft", "pending"), "draft")
        self.assertIsNone(reconcile_line("approved", "approved"))


class StoredLineTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.user = User(
            email="field@example.com",
            hashed_password="x",
            full_name="Field User",
            role=UserRole.SALES,
        )
        self.db.add(self.user)
        self.db.flush()
        self.gl = GLAccount(account_code="6100", account_name="Vehicle fuel", is_active=True)
        self.category = Category(name="Fuel", is_active=True)
        self.db.add(self.gl)
        self.db.add(self.category)
        self.db.flush()
        self.db.add(GLAccountMapping(category_id=self.category.id, gl_account_id=self.gl.id))
        self.report = ExpenseReport(
            user_id=self.user.id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 31),
            title="October 2026",
            total_amount=0,
            currency="USD",
            expense_count=0,
            status=ReportStatus.DRAFT,
        )
        self.db.add(self.report)
        self.db.flush()

    def tearDown(self):
        self.db.close()

    def line(self, amount="12.50", day=date(2026, 10, 2)):
        expense = Expense(
            user_id=self.user.id,
            amount=Decimal(amount),
            currency="USD",
            merchant_name="Shell",
            expense_date=day,
            status=ExpenseStatus.DRAFT,
            report_id=self.report.id,
            category_id=self.category.id,
            gl_account_id=self.gl.id,
        )
        self.db.add(expense)
        self.db.flush()
        return expense

    def test_removing_a_receipt_drops_it_from_the_total_and_keeps_the_row(self):
        expense = self.line()
        from app.services.reports import refresh_report
        refresh_report(self.db, self.report)
        self.assertEqual(self.report.expense_count, 1)
        take_line_off(self.db, expense, datetime(2026, 10, 3))
        self.assertEqual(self.report.expense_count, 0)
        self.assertEqual(self.report.total_amount, Decimal("0.00"))
        self.assertIsNotNone(expense.removed_at)
        self.assertIsNotNone(self.db.query(Expense).filter(Expense.id == expense.id).first())

    def test_a_new_date_moves_the_receipt_onto_the_report_that_covers_it(self):
        expense = self.line()
        landed, message = save_line(self.db, expense, "Shell", "15.00", date(2026, 11, 4), self.category.id)
        self.assertEqual(landed.title, "November 2026")
        self.assertIn("November 2026", message)
        self.assertEqual(self.report.expense_count, 0)
        self.assertEqual(landed.total_amount, Decimal("15.00"))

    def test_submitting_a_report_marks_its_receipts_waiting(self):
        expense = self.line()
        self.report.status = ReportStatus.SUBMITTED
        stamp_lines(self.db, self.report)
        self.assertEqual(expense.status, ExpenseStatus.PENDING)
        self.report.status = ReportStatus.DRAFT
        stamp_lines(self.db, self.report)
        self.assertEqual(expense.status, ExpenseStatus.DRAFT)
        self.assertIsNone(expense.submitted_at)

    def test_correcting_a_receipt_keeps_it_on_the_report_you_opened(self):
        expense = self.line()
        narrow = ExpenseReport(
            user_id=self.user.id,
            period_start=date(2026, 10, 1),
            period_end=date(2026, 10, 5),
            title="Dallas",
            total_amount=0,
            currency="USD",
            expense_count=0,
            status=ReportStatus.DRAFT,
        )
        self.db.add(narrow)
        self.db.flush()
        landed, message = save_line(self.db, expense, "Shell station", "12.50", date(2026, 10, 2), self.category.id)
        self.assertEqual(message, "Saved.")
        self.assertEqual(landed.id, self.report.id)

    def test_a_receipt_with_no_report_yet_lands_on_the_month(self):
        expense = Expense(
            user_id=self.user.id,
            amount=Decimal("8.00"),
            currency="USD",
            merchant_name="Cafe",
            expense_date=date(2026, 10, 9),
            status=ExpenseStatus.DRAFT,
        )
        self.db.add(expense)
        self.db.flush()
        landed, message = place_expense(self.db, expense)
        self.assertEqual(landed.id, self.report.id)
        self.assertIn("October 2026", message)
