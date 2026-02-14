"""
HubSpot CRM contact sync service.

Uses HubSpot Contacts v3 API via httpx.
Env var: HUBSPOT_PRIVATE_APP_TOKEN (required in production, optional in dev).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

HUBSPOT_TOKEN: str = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN", "")
HUBSPOT_BASE: str = "https://api.hubapi.com"
TIMEOUT = httpx.Timeout(10.0, read=30.0)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_configured() -> bool:
    return bool(HUBSPOT_TOKEN)


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {HUBSPOT_TOKEN}",
        "Content-Type": "application/json",
    }


def _split_name(full_name: Optional[str]) -> tuple[str, str]:
    """Split 'John Doe' into ('John', 'Doe')."""
    if not full_name or not full_name.strip():
        return ("", "")
    parts = full_name.strip().split(None, 1)
    return (parts[0], parts[1] if len(parts) > 1 else "")


def _build_properties(
    email: str,
    full_name: Optional[str],
    subscription_tier: str,
    subscription_status: str,
    user_id: int,
    created_at: Optional[datetime] = None,
) -> Dict[str, str]:
    """Build HubSpot contact properties dict."""
    firstname, lastname = _split_name(full_name)
    props: Dict[str, str] = {
        "email": email,
        "firstname": firstname,
        "lastname": lastname,
        "app_user_id": str(user_id),
        "app_subscription_tier": subscription_tier,
        "app_user_status": subscription_status,
    }
    if created_at:
        # HubSpot date properties expect epoch milliseconds
        props["app_signup_date"] = str(int(created_at.timestamp() * 1000))
    return props


def _find_contact_by_email(client: httpx.Client, email: str) -> Optional[str]:
    """Search HubSpot for a contact by email, return their HubSpot ID."""
    url = f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search"
    payload = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "email",
                "operator": "EQ",
                "value": email,
            }]
        }],
        "limit": 1,
    }
    try:
        resp = client.post(url, json=payload, headers=_headers())
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            return results[0]["id"]
    except Exception:
        logger.exception("HubSpot search failed for email=%s", email)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sync_contact_to_hubspot(
    user_id: int,
    email: str,
    full_name: Optional[str] = None,
    subscription_tier: str = "observer",
    subscription_status: str = "active",
    created_at: Optional[datetime] = None,
) -> None:
    """
    Upsert a single contact to HubSpot.  Idempotent by email.

    Designed to be called as a FastAPI BackgroundTask — must not raise.
    Logs errors instead of propagating them.
    """
    if not _is_configured():
        logger.debug("HubSpot token not configured; skipping contact sync.")
        return

    properties = _build_properties(
        email=email,
        full_name=full_name,
        subscription_tier=subscription_tier,
        subscription_status=subscription_status,
        user_id=user_id,
        created_at=created_at,
    )

    url = f"{HUBSPOT_BASE}/crm/v3/objects/contacts"

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            # Attempt to create the contact
            resp = client.post(
                url,
                json={"properties": properties},
                headers=_headers(),
            )

            if resp.status_code == 409:
                # Contact already exists — resolve ID and update
                conflict_body = resp.json()
                existing_id = None

                # HubSpot 409 message contains "Existing ID: <id>"
                msg = conflict_body.get("message", "")
                if "Existing ID:" in msg:
                    existing_id = msg.split("Existing ID:")[1].strip().rstrip(".")

                if not existing_id:
                    existing_id = _find_contact_by_email(client, email)

                if existing_id:
                    patch_resp = client.patch(
                        f"{url}/{existing_id}",
                        json={"properties": properties},
                        headers=_headers(),
                    )
                    patch_resp.raise_for_status()
                    logger.info(
                        "HubSpot contact updated: email=%s hubspot_id=%s",
                        email, existing_id,
                    )
                else:
                    logger.warning(
                        "HubSpot 409 but could not resolve contact ID: email=%s",
                        email,
                    )

            elif resp.status_code in (200, 201):
                hs_id = resp.json().get("id", "unknown")
                logger.info(
                    "HubSpot contact created: email=%s hubspot_id=%s",
                    email, hs_id,
                )
            else:
                resp.raise_for_status()

    except Exception:
        # Swallow — signup must never fail because of HubSpot
        logger.exception("HubSpot sync failed for email=%s", email)


def batch_upsert_contacts(
    contacts: List[Dict[str, Any]],
    batch_size: int = 100,
    delay_seconds: float = 1.0,
) -> Dict[str, int]:
    """
    Batch upsert contacts to HubSpot.

    Each item in *contacts* should have keys:
        email, full_name, subscription_tier, subscription_status, user_id, created_at

    Uses ``POST /crm/v3/objects/contacts/batch/upsert`` (idProperty=email).
    HubSpot batch limit: 100 per request.

    Returns ``{"created": N, "updated": N, "failed": N}``.
    """
    if not _is_configured():
        logger.warning("HubSpot token not configured; skipping batch upsert.")
        return {"created": 0, "updated": 0, "failed": 0}

    url = f"{HUBSPOT_BASE}/crm/v3/objects/contacts/batch/upsert"
    stats: Dict[str, int] = {"created": 0, "updated": 0, "failed": 0}

    for i in range(0, len(contacts), batch_size):
        batch = contacts[i : i + batch_size]
        inputs = []
        for c in batch:
            props = _build_properties(
                email=c["email"],
                full_name=c.get("full_name"),
                subscription_tier=c.get("subscription_tier", "observer"),
                subscription_status=c.get("subscription_status", "active"),
                user_id=c["user_id"],
                created_at=c.get("created_at"),
            )
            inputs.append({
                "idProperty": "email",
                "id": c["email"],
                "properties": props,
            })

        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.post(url, json={"inputs": inputs}, headers=_headers())
                resp.raise_for_status()
                data = resp.json()
                n = len(data.get("results", []))
                # batch/upsert doesn't distinguish created vs updated in results
                stats["updated"] += n
                logger.info(
                    "HubSpot batch %d–%d: %d contacts upserted.",
                    i, i + len(batch) - 1, n,
                )
        except Exception:
            logger.exception(
                "HubSpot batch upsert failed for batch starting at index %d", i,
            )
            stats["failed"] += len(batch)

        # Rate-limit safety
        if i + batch_size < len(contacts):
            time.sleep(delay_seconds)

    logger.info("HubSpot batch upsert complete: %s", stats)
    return stats
