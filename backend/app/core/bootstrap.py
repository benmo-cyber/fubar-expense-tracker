def planned_users(environment: str, has_users: bool, admin_email: str, admin_password: str, admin_name: str) -> list[dict]:
    """Who to create when the database has no users.

    Development gets the local sample accounts. Production creates one admin
    from the server environment, and creates nobody if that password was not set.
    """
    if has_users:
        return []
    if environment == "production":
        email = (admin_email or "").strip()
        password = admin_password or ""
        if not email or not password:
            return []
        return [{
            "email": email,
            "password": password,
            "full_name": (admin_name or "").strip() or "Admin",
            "role": "admin",
        }]
    return [
        {
            "email": "admin@example.com",
            "password": "AdminPass1",
            "full_name": "Admin",
            "role": "admin",
        },
        {
            "email": "field@example.com",
            "password": "FieldPass1",
            "full_name": "Field User",
            "role": "operations",
        },
    ]
