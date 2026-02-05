from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Auth
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # 2FA
    is_2fa_enabled = Column(Boolean, default=False)
    twofa_secret = Column(String, nullable=True)
    backup_codes = Column(JSON, nullable=True)

    # Trusted devices
    trusted_devices = Column(JSON, nullable=True)

    # -------------------------
    # Subscription / plan gating
    # -------------------------
    # observer | signals | pro
    subscription_tier = Column(String, default="observer", nullable=False)

    # active | past_due | canceled | trialing (etc.)
    subscription_status = Column(String, default="active", nullable=False)

    # Provider IDs (Stripe later)
    subscription_provider = Column(String, nullable=True)  # e.g., "stripe"
    subscription_provider_customer_id = Column(String, nullable=True)
    subscription_provider_subscription_id = Column(String, nullable=True)

    # Timestamps
    subscription_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
