"""
One-time backfill: sync all existing DB users to HubSpot as contacts.

Usage (from Platform/api/):

    python -m scripts.backfill_hubspot

Or directly:

    python scripts/backfill_hubspot.py

Requires HUBSPOT_PRIVATE_APP_TOKEN in environment or .env file.
"""
from __future__ import annotations

import logging
import os
import sys

# Ensure app package is importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.hubspot_service import batch_upsert_contacts  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN")
    if not token:
        logger.error("HUBSPOT_PRIVATE_APP_TOKEN not set. Aborting.")
        sys.exit(1)

    db = SessionLocal()
    try:
        users = db.query(User).all()
        logger.info("Found %d user(s) in database.", len(users))

        if not users:
            logger.info("No users to sync. Done.")
            return

        contacts = []
        for u in users:
            contacts.append({
                "email": u.email,
                "full_name": getattr(u, "full_name", None),
                "subscription_tier": u.subscription_tier,
                "subscription_status": u.subscription_status,
                "user_id": u.id,
                "created_at": u.created_at,
            })

        logger.info("Starting HubSpot batch upsert for %d contact(s)...", len(contacts))
        stats = batch_upsert_contacts(
            contacts,
            batch_size=100,
            delay_seconds=1.0,
        )
        logger.info("Backfill complete. Stats: %s", stats)

    finally:
        db.close()


if __name__ == "__main__":
    main()
