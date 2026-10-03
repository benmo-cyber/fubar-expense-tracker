"""Add new columns to the existing SQLite database without a separate migration step."""
from sqlalchemy import inspect, text
from app.core.database import Base, engine


COLUMN_PATCHES = {
    "users": {
        "is_superuser": "BOOLEAN DEFAULT 0",
        "supervisor_id": "CHAR(32)",
    },
    "expenses": {
        "merchant_id": "CHAR(32)",
        "report_id": "CHAR(32)",
        "trip_id": "CHAR(32)",
    },
    "expense_reports": {
        "title": "VARCHAR(255)",
        "review_notes": "TEXT",
        "reviewed_by": "CHAR(32)",
        "submitted_at": "DATETIME",
        "screenshot_url": "VARCHAR(500)",
    },
}


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, columns in COLUMN_PATCHES.items():
            if table not in inspector.get_table_names():
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, declaration in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"))
