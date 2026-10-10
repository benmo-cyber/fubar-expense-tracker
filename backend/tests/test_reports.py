import unittest
from decimal import Decimal

from app.services.reports import can_view_report, report_total, team_member_ids


PEOPLE = [
    {"id": "ben", "supervisor_id": None},
    {"id": "lead", "supervisor_id": "ben"},
    {"id": "rep", "supervisor_id": "lead"},
    {"id": "other", "supervisor_id": "ben"},
]


class ReportTotalTests(unittest.TestCase):
    def test_a_second_receipt_can_be_a_plain_number_beside_a_decimal(self):
        self.assertEqual(report_total([Decimal("20.00"), 5.0]), Decimal("25.00"))
        self.assertEqual(report_total([None]), Decimal("0.00"))


class TeamReportTests(unittest.TestCase):
    def test_a_supervisor_sees_the_whole_branch_under_them(self):
        self.assertEqual(team_member_ids("lead", PEOPLE), {"rep"})
        self.assertEqual(team_member_ids("ben", PEOPLE), {"lead", "rep", "other"})
        self.assertEqual(team_member_ids("rep", PEOPLE), set())

    def test_a_supervisor_can_open_an_unfinished_report_from_their_team(self):
        self.assertTrue(can_view_report("lead", False, "rep", "draft", PEOPLE))
        self.assertTrue(can_view_report("lead", False, "rep", "submitted", PEOPLE))
        self.assertTrue(can_view_report("ben", False, "rep", "rejected", PEOPLE))
        self.assertFalse(can_view_report("lead", False, "rep", "approved", PEOPLE))
        self.assertFalse(can_view_report("lead", False, "other", "draft", PEOPLE))
        self.assertTrue(can_view_report("rep", False, "rep", "approved", PEOPLE))
        self.assertTrue(can_view_report("other", True, "rep", "approved", PEOPLE))

    def test_a_loop_in_the_chart_does_not_keep_walking(self):
        looped = [
            {"id": "a", "supervisor_id": "b"},
            {"id": "b", "supervisor_id": "a"},
        ]
        self.assertEqual(team_member_ids("a", looped), {"b"})
