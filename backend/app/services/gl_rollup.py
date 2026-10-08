"""Parent and child GL accounts, and the rollup an admin sees."""
from decimal import Decimal, ROUND_HALF_UP

UNASSIGNED = "unassigned"


class ParentLinkError(ValueError):
    pass


def normalize_parent_request(
    child_code: str,
    parent_code: str | None,
    parent_name: str | None,
    known_codes: set[str],
) -> tuple[str, str] | None:
    code = (parent_code or "").strip()
    name = (parent_name or "").strip()
    if not code:
        return None
    if code == (child_code or "").strip():
        raise ParentLinkError("An account cannot roll up to itself.")
    if code not in known_codes and not name:
        raise ParentLinkError("Enter a name for the parent account.")
    return code, name


def validate_parent(account_id: str, parent_id: str | None, parents: dict[str, str | None]) -> None:
    if not parent_id:
        return
    if parent_id == account_id:
        raise ParentLinkError("An account cannot roll up to itself.")
    if parent_id not in parents:
        raise ParentLinkError("That parent account was not found.")
    seen: set[str] = set()
    current: str | None = parent_id
    while current:
        if current == account_id:
            raise ParentLinkError("That parent is already under this account.")
        if current in seen:
            raise ParentLinkError("That parent is part of a loop.")
        seen.add(current)
        current = parents.get(current)


def _root(account_id: str, parents: dict[str, str | None]) -> str:
    seen: set[str] = set()
    current = account_id
    while True:
        parent = parents.get(current)
        if not parent or parent not in parents or parent in seen:
            return current
        seen.add(current)
        current = parent


def _child_under_root(account_id: str, root: str, parents: dict[str, str | None]) -> str | None:
    if account_id == root:
        return None
    seen: set[str] = set()
    current = account_id
    while current != root:
        if current in seen:
            return account_id
        seen.add(current)
        parent = parents.get(current)
        if not parent:
            return account_id
        if parent == root:
            return current
        current = parent
    return None


def _share(info: dict, amount: Decimal, total: Decimal, posted_here: bool) -> dict:
    percent = Decimal("0.0")
    if total:
        percent = (amount / total * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return {
        "id": info.get("id"),
        "code": info.get("code") or "",
        "name": info.get("name") or "Unassigned",
        "amount": amount,
        "percent": percent,
        "posted_here": posted_here,
    }


def spending_groups(lines: list[tuple[str, Decimal]], accounts: list[dict]) -> list[dict]:
    catalog = {row["id"]: row for row in accounts}
    parents = {row["id"]: row.get("parent_id") for row in accounts}
    by_root: dict[str, Decimal] = {}
    by_child: dict[tuple[str, str], Decimal] = {}
    direct: dict[str, Decimal] = {}
    for account_id, amount in lines:
        amount = Decimal(amount or 0)
        if amount == 0:
            continue
        if account_id not in catalog:
            catalog[account_id] = {"id": account_id, "code": "", "name": "Unassigned", "parent_id": None}
            parents[account_id] = None
        root = _root(account_id, parents)
        by_root[root] = by_root.get(root, Decimal("0")) + amount
        child = _child_under_root(account_id, root, parents)
        if child is None:
            direct[root] = direct.get(root, Decimal("0")) + amount
        else:
            by_child[(root, child)] = by_child.get((root, child), Decimal("0")) + amount

    groups = []
    for root, total in by_root.items():
        info = catalog.get(root, {"id": root, "code": "", "name": "Unassigned"})
        child_ids = {child for (group, child) in by_child if group == root}
        children = []
        if child_ids and direct.get(root):
            children.append(_share(info, direct[root], total, posted_here=True))
        for child in child_ids:
            child_info = catalog.get(child, {"id": child, "code": "", "name": "Unassigned"})
            children.append(_share(child_info, by_child[(root, child)], total, posted_here=False))
        children.sort(key=lambda row: (row["code"], row["name"]))
        groups.append({
            "id": root,
            "code": info.get("code") or "",
            "name": info.get("name") or "Unassigned",
            "amount": total,
            "children": children,
        })
    groups.sort(key=lambda row: (row["code"] == "", row["code"], row["name"]))
    return groups


def gl_catalog(accounts) -> list[dict]:
    rows = [
        {
            "id": str(account.id),
            "code": account.account_code,
            "name": account.account_name,
            "parent_id": str(account.parent_id) if account.parent_id else None,
        }
        for account in accounts
    ]
    rows.append({"id": UNASSIGNED, "code": "", "name": "Unassigned", "parent_id": None})
    return rows


def groups_as_numbers(groups: list[dict]) -> list[dict]:
    return [
        {
            **group,
            "amount": float(group["amount"]),
            "children": [
                {**child, "amount": float(child["amount"]), "percent": float(child["percent"])}
                for child in group["children"]
            ],
        }
        for group in groups
    ]


def rollup(lines: list[tuple[str, Decimal]], accounts) -> list[dict]:
    return groups_as_numbers(spending_groups(lines, gl_catalog(accounts)))
