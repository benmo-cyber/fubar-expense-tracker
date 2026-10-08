"""Point an expense account at a GL account, and release one that was removed."""


class AssignError(ValueError):
    pass


def posted_gl_name(account_name: str, gl_name: str | None) -> str:
    """The expense account name is the GL name. A separate GL name is optional."""
    chosen = (gl_name or "").strip()
    if chosen:
        return chosen
    name = (account_name or "").strip()
    if not name:
        raise AssignError("Enter an account name.")
    return name


def posting_gl_id(gl_account_id: str | None, is_active: bool) -> str | None:
    """A receipt posts only to a GL account that is still in use."""
    if gl_account_id and is_active:
        return gl_account_id
    return None


def expense_account_gl(account: dict | None) -> dict:
    """Hide a removed GL so the expense account can be pointed somewhere else."""
    blank = {
        "gl_account_id": None,
        "gl_code": None,
        "gl_name": None,
        "parent_id": None,
        "parent_code": None,
        "parent_name": None,
        "removed_code": None,
        "removed_name": None,
    }
    if not account:
        return blank
    if not account.get("is_active", True):
        blank["removed_code"] = account.get("code") or None
        blank["removed_name"] = account.get("name") or None
        return blank
    parent_ok = bool(account.get("parent_id")) and account.get("parent_active", True)
    return {
        "gl_account_id": account.get("id"),
        "gl_code": account.get("code"),
        "gl_name": account.get("name"),
        "parent_id": account.get("parent_id") if parent_ok else None,
        "parent_code": account.get("parent_code") if parent_ok else None,
        "parent_name": account.get("parent_name") if parent_ok else None,
        "removed_code": None,
        "removed_name": None,
    }


def choose_reassignment(
    gl_account_id: str | None,
    gl_code: str | None,
    gl_name: str | None,
    accounts: list[dict],
) -> dict:
    """Pick an existing GL account, bring a removed code back, or create a new one."""
    account_id = (gl_account_id or "").strip()
    code = (gl_code or "").strip()
    name = (gl_name or "").strip()
    by_id = {row["id"]: row for row in accounts}
    by_code = {row["code"]: row for row in accounts}

    if account_id:
        found = by_id.get(account_id)
        if not found:
            raise AssignError("That GL account was not found.")
        if not found.get("is_active", True):
            raise AssignError("That GL account was removed. Enter its code to use it again.")
        return {"kind": "use", "id": found["id"]}

    if not code:
        raise AssignError("Choose a GL account.")

    found = by_code.get(code)
    if found:
        if found.get("is_active", True):
            return {"kind": "use", "id": found["id"]}
        return {"kind": "reactivate", "id": found["id"], "name": name or found.get("name") or ""}

    if not name:
        raise AssignError("Enter a name for the GL account.")
    return {"kind": "create", "code": code, "name": name}


def links_released_by_removal(
    account_id: str,
    mapping_ids_by_gl: dict[str, list[str]],
    parents: dict[str, str | None],
) -> tuple[list[str], list[str]]:
    """Expense accounts and child GL accounts that were hanging off a removed account."""
    mapping_ids = list(mapping_ids_by_gl.get(account_id, []))
    children = [child for child, parent in parents.items() if parent == account_id]
    return mapping_ids, children
