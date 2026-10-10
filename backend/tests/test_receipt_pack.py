import unittest
import zipfile
import io

from app.services.receipt_pack import (
    grouped_receipts,
    pack_report,
    receipt_filename,
    receipt_folder_name,
)


class ReceiptFolderTests(unittest.TestCase):
    def test_the_folder_uses_the_person_and_the_report_title(self):
        self.assertEqual(
            receipt_folder_name("Ben Morris", "October 2026"),
            "Ben Morris October 2026 receipts",
        )

    def test_a_trip_gets_its_own_folder_and_other_receipts_use_the_report(self):
        groups = grouped_receipts("Ben Morris", "October 2026", [
            {"expense_date": "2026-10-02", "merchant_name": "Staples", "amount": 8, "receipt_url": "/uploads/receipts/a.jpg"},
            {"expense_date": "2026-10-01", "merchant_name": "Hotel", "amount": 140.5, "trip_name": "Dallas", "receipt_url": "/uploads/receipts/b.HEIC"},
            {"merchant_name": "No photo", "amount": 3, "receipt_url": ""},
        ])
        self.assertEqual([name for name, _files in groups], [
            "Ben Morris October 2026 receipts",
            "Ben Morris Dallas receipts",
        ])
        report_files = groups[0][1]
        trip_files = groups[1][1]
        self.assertEqual(report_files[0][0], "2026-10-02 Staples 8.00.jpg")
        self.assertEqual(trip_files[0][0], "2026-10-01 Hotel 140.50.heic")

    def test_two_receipts_from_the_same_stop_keep_separate_names(self):
        taken: set[str] = set()
        expense = {"expense_date": "2026-10-01", "merchant_name": "Cafe", "amount": 4.25, "receipt_url": "/r.jpg"}
        first = receipt_filename(expense, taken)
        second = receipt_filename(expense, taken)
        self.assertEqual(first, "2026-10-01 Cafe 4.25.jpg")
        self.assertEqual(second, "2026-10-01 Cafe 4.25 2.jpg")

    def test_the_zip_holds_the_spreadsheet_beside_the_receipt_folder(self):
        payload = pack_report(
            "Ben Morris October 2026.xlsx",
            b"sheet",
            [("Ben Morris October 2026 receipts", [("2026-10-01 Cafe 4.25.jpg", b"photo")])],
        )
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                [
                    "Ben Morris October 2026 receipts/2026-10-01 Cafe 4.25.jpg",
                    "Ben Morris October 2026.xlsx",
                ],
            )
            self.assertEqual(archive.read("Ben Morris October 2026.xlsx"), b"sheet")
            self.assertEqual(archive.read("Ben Morris October 2026 receipts/2026-10-01 Cafe 4.25.jpg"), b"photo")
