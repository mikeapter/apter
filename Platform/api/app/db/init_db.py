"""Database initialization helpers.

We intentionally keep this simple (no Alembic yet).
On startup we:
  1) import model modules so SQLAlchemy registers tables
  2) create missing tables in sqlite
  3) run lightweight column migrations for new nullable columns

If you later add Alembic migrations, this file can become a no-op.
"""

import logging

from app.db.base import Base
from app.db.session import engine

# Import models so they register on Base.metadata
from app.models.user import User  # noqa: F401

logger = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_add_full_name()


def _migrate_add_full_name() -> None:
    """One-time migration: add full_name column if missing (safe for SQLite)."""
    try:
        conn = engine.raw_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "full_name" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR")
            conn.commit()
            logger.info("Migration: added 'full_name' column to users table.")
        conn.close()
    except Exception:
        logger.exception("Migration check for full_name failed (non-fatal).")
