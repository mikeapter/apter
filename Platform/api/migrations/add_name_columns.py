"""
Migration: Add first_name and last_name columns to users table.

Safe for existing data:
  - Columns are nullable with default empty string
  - Existing rows get empty string (not NULL)
  - No data loss, fully reversible

Works with both SQLite (local dev) and PostgreSQL (production).

Run:
  cd Platform/api
  python -m migrations.add_name_columns

Rollback:
  cd Platform/api
  python -m migrations.add_name_columns --rollback
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text


def get_engine():
    """Create engine from DATABASE_URL env var, falling back to local SQLite."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./bottrader.db")
    # Render provides postgres:// but SQLAlchemy 2.x requires postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(db_url, connect_args=connect_args)


def get_existing_columns(engine, table: str) -> set[str]:
    """Get existing column names (works with SQLite and PostgreSQL)."""
    insp = inspect(engine)
    if not insp.has_table(table):
        return set()
    return {col["name"] for col in insp.get_columns(table)}


def migrate():
    engine = get_engine()
    print(f"Database: {engine.url}")

    existing = get_existing_columns(engine, "users")
    if not existing:
        print("  Table 'users' not found. Nothing to migrate.")
        return

    added = []
    with engine.begin() as conn:
        if "first_name" not in existing:
            conn.execute(text("ALTER TABLE users ADD COLUMN first_name VARCHAR DEFAULT ''"))
            added.append("first_name")
            print("  Added column: first_name")
        else:
            print("  Column first_name already exists, skipping.")

        if "last_name" not in existing:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_name VARCHAR DEFAULT ''"))
            added.append("last_name")
            print("  Added column: last_name")
        else:
            print("  Column last_name already exists, skipping.")

        # Ensure existing NULL values are set to empty string
        if added:
            conn.execute(text("UPDATE users SET first_name = '' WHERE first_name IS NULL"))
            conn.execute(text("UPDATE users SET last_name = '' WHERE last_name IS NULL"))
            print("  Backfilled NULL values to empty string.")

    print("Migration complete.")


def rollback():
    engine = get_engine()
    print(f"Database: {engine.url}")

    existing = get_existing_columns(engine, "users")

    with engine.begin() as conn:
        if "first_name" in existing:
            conn.execute(text("ALTER TABLE users DROP COLUMN first_name"))
            print("  Dropped column: first_name")
        if "last_name" in existing:
            conn.execute(text("ALTER TABLE users DROP COLUMN last_name"))
            print("  Dropped column: last_name")

    print("Rollback complete.")


if __name__ == "__main__":
    if "--rollback" in sys.argv:
        rollback()
    else:
        migrate()
