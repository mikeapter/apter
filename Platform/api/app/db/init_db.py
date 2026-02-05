"""Database initialization helpers.

We intentionally keep this simple (no Alembic yet).
On startup we:
  1) import model modules so SQLAlchemy registers tables
  2) create missing tables in sqlite

If you later add Alembic migrations, this file can become a no-op.
"""

from app.db.base import Base
from app.db.session import engine

# Import models so they register on Base.metadata
from app.models.user import User  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
