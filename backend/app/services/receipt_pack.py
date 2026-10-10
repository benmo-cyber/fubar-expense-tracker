import io
import re
import zipfile
from pathlib import Path


_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_SPACES = re.compile(r"\s+")
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".heic"}


def bundle_name(user_name: str, label: str) -> str:
    """The readable name shared by the spreadsheet and its receipt folder."""
    person = (user_name or "").strip() or "Report"
    title = (label or "").strip() or "Expenses"
    return _safe(f"{person} {title}")


def receipt_folder_name(user_name: str, label: str) -> str:
    """Folder name such as 'Ben Morris October 2026 receipts'."""
    return f"{bundle_name(user_name, label)} receipts"


def receipt_filename(expense: dict, taken: set[str]) -> str:
    """A receipt file named from its date, merchant, and amount."""
    date = (expense.get("expense_date") or "undated").strip() or "undated"
    merchant = (expense.get("merchant_name") or "receipt").strip() or "receipt"
    amount = expense.get("amount")
    amount_text = f"{float(amount):.2f}" if isinstance(amount, (int, float)) else ""
    extension = _extension(expense.get("receipt_url"))
    base = _safe(" ".join(part for part in (date, merchant, amount_text) if part))
    name = f"{base}{extension}"
    number = 2
    while name.lower() in taken:
        name = f"{base} {number}{extension}"
        number += 1
    taken.add(name.lower())
    return name


def grouped_receipts(user_name: str, title: str, expenses: list[dict]) -> list[tuple[str, list[tuple[str, dict]]]]:
    """Receipts filed on a trip use the trip name. The rest use the report title."""
    groups: dict[str, list[tuple[str, dict]]] = {}
    taken: dict[str, set[str]] = {}
    for expense in expenses:
        if not (expense.get("receipt_url") or "").strip():
            continue
        label = (expense.get("trip_name") or "").strip() or title
        folder = receipt_folder_name(user_name, label)
        names = taken.setdefault(folder, set())
        groups.setdefault(folder, []).append((receipt_filename(expense, names), expense))
    return list(groups.items())


def pack_report(spreadsheet_name: str, spreadsheet: bytes, folders: list[tuple[str, list[tuple[str, bytes]]]]) -> bytes:
    """Zip the spreadsheet beside one folder of receipt files per trip or report."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(spreadsheet_name, spreadsheet)
        for folder, files in folders:
            for filename, content in files:
                archive.writestr(f"{folder}/{filename}", content)
    return buffer.getvalue()


def _safe(value: str) -> str:
    text = _SPACES.sub(" ", _UNSAFE.sub(" ", value)).strip(" .")
    return text or "Receipts"


def _extension(url: str | None) -> str:
    suffix = Path(str(url or "")).suffix.lower()
    if suffix in _ALLOWED_EXTENSIONS:
        return suffix
    return ".jpg"
