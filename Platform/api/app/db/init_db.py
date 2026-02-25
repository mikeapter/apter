"""Database initialization helpers.

We intentionally keep this simple (no Alembic yet).
On startup we:
  1) import model modules so SQLAlchemy registers tables
  2) create missing tables via SQLAlchemy
  3) run lightweight column migrations for new nullable columns

Works with both SQLite (local dev) and PostgreSQL (production).
If you later add Alembic migrations, this file can become a no-op.
"""

import logging

from sqlalchemy import inspect

from app.db.base import Base
from app.db.session import engine

# Import models so they register on Base.metadata
from app.models.user import User  # noqa: F401

logger = logging.getLogger(__name__)


def _get_existing_columns(table_name: str) -> set[str]:
    """Get existing column names for a table (works with SQLite and PostgreSQL)."""
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return set()
    return {col["name"] for col in insp.get_columns(table_name)}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def _migrate_add_columns() -> None:
    """One-time migrations: add columns if missing (safe for SQLite & PostgreSQL)."""
    try:
        existing = _get_existing_columns("users")
        if not existing:
            return  # Table doesn't exist yet or is empty; create_all handles it

        columns_to_add = {
            "full_name": "VARCHAR",
            "first_name": "VARCHAR DEFAULT ''",
            "last_name": "VARCHAR DEFAULT ''",
            "is_active": "BOOLEAN DEFAULT true NOT NULL",
        }

        with engine.begin() as conn:
            for col_name, col_type in columns_to_add.items():
                if col_name not in existing:
                    conn.execute(
                        __import__("sqlalchemy").text(
                            f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                        )
                    )
                    logger.info("Migration: added '%s' column to users table.", col_name)

    except Exception:
        logger.exception("Migration check for user columns failed (non-fatal).")
