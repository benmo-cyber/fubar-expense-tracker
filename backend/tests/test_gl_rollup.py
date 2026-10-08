import unittest
from decimal import Decimal

from app.services.gl_rollup import (
    ParentLinkError,
    normalize_parent_request,
    parent_code_for,
    parent_on_open,
    spending_groups,
    validate_parent,
)


def account(account_id, code, name, parent_id=None):
    return {"id": account_id, "code": code, "name": name, "parent_id": parent_id}


class ChartCodeTests(unittest.TestCase):
    def test_opening_the_chart_leaves_a_removed_parent_removed(self):
        self.assertEqual(parent_on_open(None), "create")
        self.assertEqual(parent_on_open(True), "keep")
        self.assertEqual(parent_on_open(False), "leave")

    def test_the_first_two_digits_name_the_parent(self):
        self.assertIsNone(parent_code_for("6400"))
        self.assertEqual(parent_code_for("6410"), "6400")
        self.assertEqual(parent_code_for("6415"), "6400")
        self.assertIsNone(parent_code_for("6200"))

    def test_a_code_has_to_be_four_digits(self):
        with self.assertRaises(ParentLinkError):
            parent_code_for("64")
        with self.assertRaises(ParentLinkError):
            parent_code_for("641")
        with self.assertRaises(ParentLinkError):
            parent_code_for("64A0")


class ParentLinkTests(unittest.TestCase):
    def test_a_new_parent_needs_a_name_and_cannot_be_the_same_account(self):
        self.assertIsNone(normalize_parent_request("6410", "", "", set()))
        self.assertEqual(
            normalize_parent_request("6410", "6400", "", {"6400"}),
            ("6400", ""),
        )
        with self.assertRaises(ParentLinkError):
            normalize_parent_request("6410", "6410", "Travel expense", set())
        with self.assertRaises(ParentLinkError):
            normalize_parent_request("6410", "6400", "", set())

    def test_parent_cannot_loop_back_to_itself(self):
        parents = {"6400": None, "6410": "6400", "6411": "6410"}
        validate_parent("6415", "6400", parents)
        with self.assertRaises(ParentLinkError):
            validate_parent("6400", "6400", parents)
        with self.assertRaises(ParentLinkError):
            validate_parent("6400", "6411", parents)
        with self.assertRaises(ParentLinkError):
            validate_parent("6410", "missing", parents)


class SpendingGroupTests(unittest.TestCase):
    def setUp(self):
        self.accounts = [
            account("parent", "6400", "Travel & Meals"),
            account("travel", "6410", "Travel expense", "parent"),
            account("meals", "6415", "Travel - employee meals", "parent"),
            account("air", "6411", "Airfare", "travel"),
            account("fuel", "6100", "Vehicle fuel"),
        ]

    def test_children_show_their_share_of_the_parent(self):
        groups = spending_groups(
            [("travel", Decimal("200")), ("meals", Decimal("100"))],
            self.accounts,
        )
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group["code"], "6400")
        self.assertEqual(group["amount"], Decimal("300"))
        self.assertEqual(
            [(child["code"], child["amount"], child["percent"]) for child in group["children"]],
            [("6410", Decimal("200"), Decimal("66.7")), ("6415", Decimal("100"), Decimal("33.3"))],
        )

    def test_a_deeper_account_rolls_into_the_account_directly_under_the_parent(self):
        groups = spending_groups(
            [("air", Decimal("50")), ("meals", Decimal("50"))],
            self.accounts,
        )
        children = [(child["code"], child["amount"], child["percent"]) for child in groups[0]["children"]]
        self.assertEqual(children, [("6410", Decimal("50"), Decimal("50.0")), ("6415", Decimal("50"), Decimal("50.0"))])

    def test_an_account_with_no_parent_stands_alone(self):
        groups = spending_groups([("fuel", Decimal("40"))], self.accounts)
        self.assertEqual(groups[0]["code"], "6100")
        self.assertEqual(groups[0]["amount"], Decimal("40"))
        self.assertEqual(groups[0]["children"], [])

    def test_amount_filed_on_the_parent_is_part_of_its_total(self):
        groups = spending_groups(
            [("parent", Decimal("50")), ("meals", Decimal("50"))],
            self.accounts,
        )
        posted = next(child for child in groups[0]["children"] if child["posted_here"])
        self.assertEqual(posted["code"], "6400")
        self.assertEqual(posted["percent"], Decimal("50.0"))
        self.assertEqual(groups[0]["amount"], Decimal("100"))
