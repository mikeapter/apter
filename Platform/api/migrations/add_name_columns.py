"""
Migration: Add first_name and last_name columns to users table.

Safe for existing data:
  - Columns are nullable with default empty string
  - Existing rows get empty string (not NULL)
  - No data loss, fully reversible

Run:
  cd Platform/api
  python -m migrations.add_name_columns

Rollback:
  cd Platform/api
  python -m migrations.add_name_columns --rollback
"""

import sys
import sqlite3
import os


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "bottrader.db")
# Also check repo root (where uvicorn runs from)
DB_PATH_ALT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "bottrader.db")


def get_db_path() -> str:
    """Find the database file."""
    for p in [DB_PATH, DB_PATH_ALT]:
        resolved = os.path.abspath(p)
        if os.path.exists(resolved):
            return resolved
    # Default: create alongside api directory
    return os.path.abspath(DB_PATH_ALT)


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate():
    db_path = get_db_path()
    print(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    added = []

    if not column_exists(cursor, "users", "first_name"):
        cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT DEFAULT ''")
        added.append("first_name")
        print("  Added column: first_name")
    else:
        print("  Column first_name already exists, skipping.")

    if not column_exists(cursor, "users", "last_name"):
        cursor.execute("ALTER TABLE users ADD COLUMN last_name TEXT DEFAULT ''")
        added.append("last_name")
        print("  Added column: last_name")
    else:
        print("  Column last_name already exists, skipping.")

    # Ensure existing NULL values are set to empty string
    if added:
        cursor.execute("UPDATE users SET first_name = '' WHERE first_name IS NULL")
        cursor.execute("UPDATE users SET last_name = '' WHERE last_name IS NULL")
        print(f"  Backfilled NULL values to empty string.")

    conn.commit()
    conn.close()
    print("Migration complete.")


def rollback():
    """
    SQLite does not support DROP COLUMN in older versions.
    For SQLite 3.35+, we can drop columns directly.
    For older versions, this prints manual instructions.
    """
    db_path = get_db_path()
    print(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sqlite_version = sqlite3.sqlite_version_info

    if sqlite_version >= (3, 35, 0):
        if column_exists(cursor, "users", "first_name"):
            cursor.execute("ALTER TABLE users DROP COLUMN first_name")
            print("  Dropped column: first_name")
        if column_exists(cursor, "users", "last_name"):
            cursor.execute("ALTER TABLE users DROP COLUMN last_name")
            print("  Dropped column: last_name")
        conn.commit()
        print("Rollback complete.")
    else:
        print(f"  SQLite version {sqlite3.sqlite_version} does not support DROP COLUMN.")
        print("  To rollback manually, recreate the table without the name columns.")
        print("  Or upgrade SQLite to 3.35+.")

    conn.close()


if __name__ == "__main__":
    if "--rollback" in sys.argv:
        rollback()
    else:
        migrate()
