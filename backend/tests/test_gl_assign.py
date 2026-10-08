import unittest

from app.services.gl_rollup import ParentLinkError
from app.services.gl_assign import (
    AssignError,
    choose_reassignment,
    expense_account_gl,
    gl_removal_changes,
    links_released_by_removal,
    revised_gl,
    posted_gl_name,
    posting_gl_id,
)


ACCOUNTS = [
    {"id": "fuel", "code": "6100", "name": "Vehicle fuel", "is_active": True},
    {"id": "old", "code": "6199", "name": "Old fuel", "is_active": False},
]


class PostedNameTests(unittest.TestCase):
    def test_the_account_name_is_the_gl_name(self):
        self.assertEqual(posted_gl_name("Travel expense", None), "Travel expense")
        self.assertEqual(posted_gl_name("Travel expense", "  "), "Travel expense")
        self.assertEqual(posted_gl_name("Travel expense", "Airfare"), "Airfare")
        with self.assertRaises(AssignError):
            posted_gl_name("  ", None)


class PostingTests(unittest.TestCase):
    def test_a_receipt_posts_only_to_an_active_gl_account(self):
        self.assertEqual(posting_gl_id("fuel", True), "fuel")
        self.assertIsNone(posting_gl_id("old", False))
        self.assertIsNone(posting_gl_id(None, True))


class ExpenseAccountViewTests(unittest.TestCase):
    def test_a_removed_gl_account_leaves_the_expense_account_open_to_reassign(self):
        shown = expense_account_gl({
            "id": "old",
            "code": "6199",
            "name": "Old fuel",
            "is_active": False,
            "parent_id": "travel",
            "parent_code": "6400",
            "parent_name": "Travel & Meals",
            "parent_active": True,
        })
        self.assertIsNone(shown["gl_account_id"])
        self.assertEqual(shown["removed_code"], "6199")
        self.assertEqual(shown["removed_name"], "Old fuel")

    def test_an_active_account_keeps_its_parent_when_that_parent_is_still_in_use(self):
        shown = expense_account_gl({
            "id": "fuel",
            "code": "6100",
            "name": "Vehicle fuel",
            "is_active": True,
            "parent_id": "travel",
            "parent_code": "6400",
            "parent_name": "Travel & Meals",
            "parent_active": False,
        })
        self.assertEqual(shown["gl_code"], "6100")
        self.assertIsNone(shown["parent_id"])
        self.assertIsNone(shown["removed_code"])


class ReassignmentTests(unittest.TestCase):
    def test_choosing_an_active_account_uses_it(self):
        self.assertEqual(
            choose_reassignment("fuel", None, None, ACCOUNTS),
            {"kind": "use", "id": "fuel"},
        )

    def test_a_missing_or_removed_choice_asks_for_another_account(self):
        with self.assertRaises(AssignError):
            choose_reassignment("missing", None, None, ACCOUNTS)
        with self.assertRaises(AssignError):
            choose_reassignment("old", None, None, ACCOUNTS)
        with self.assertRaises(AssignError):
            choose_reassignment(None, "", "", ACCOUNTS)

    def test_an_existing_code_is_reused_and_a_removed_code_comes_back(self):
        self.assertEqual(
            choose_reassignment(None, "6100", "", ACCOUNTS),
            {"kind": "use", "id": "fuel"},
        )
        self.assertEqual(
            choose_reassignment(None, "6199", "Fuel again", ACCOUNTS),
            {"kind": "reactivate", "id": "old", "name": "Fuel again"},
        )

    def test_a_new_code_needs_a_name(self):
        with self.assertRaises(AssignError):
            choose_reassignment(None, "6410", "", ACCOUNTS)
        self.assertEqual(
            choose_reassignment(None, "6410", "Travel expense", ACCOUNTS),
            {"kind": "create", "code": "6410", "name": "Travel expense"},
        )

    def test_an_account_id_wins_when_a_code_is_also_sent(self):
        self.assertEqual(
            choose_reassignment("fuel", "6410", "Travel expense", ACCOUNTS),
            {"kind": "use", "id": "fuel"},
        )


class RevisionTests(unittest.TestCase):
    def test_a_correction_keeps_the_same_account_and_rejects_a_bad_code(self):
        self.assertEqual(revised_gl(" 6410 ", " Travel expense ", set()), ("6410", "Travel expense"))
        with self.assertRaises(AssignError):
            revised_gl("6410", "  ", set())
        with self.assertRaises(AssignError):
            revised_gl("6410", "Travel expense", {"6410"})
        with self.assertRaises(ParentLinkError):
            revised_gl("641", "Travel expense", set())


class RemovalTests(unittest.TestCase):
    def test_removing_a_gl_hides_it_and_leaves_filed_receipts_alone(self):
        self.assertEqual(gl_removal_changes(), {"is_active": False})

    def test_removing_a_gl_releases_its_expense_accounts_and_child_accounts(self):
        mappings, children = links_released_by_removal(
            "travel",
            {"travel": ["map-1", "map-2"], "fuel": ["map-3"]},
            {"meals": "travel", "air": "meals", "fuel": None},
        )
        self.assertEqual(mappings, ["map-1", "map-2"])
        self.assertEqual(children, ["meals"])
