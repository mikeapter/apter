# Platform/api/app/services/twofa_service.py

import logging
import os

import pyotp
import secrets
import hashlib
from cryptography.fernet import Fernet

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Fernet key for encrypting 2FA secrets at rest ────────────────────────────
# CRITICAL: Must be persistent across restarts, otherwise all existing
# 2FA secrets become undecryptable and users get locked out.
_fernet_key_raw = os.getenv("FERNET_KEY", "")

if _fernet_key_raw:
    FERNET_KEY = _fernet_key_raw.encode() if isinstance(_fernet_key_raw, str) else _fernet_key_raw
else:
    # Generate ephemeral key for development — logs a warning
    FERNET_KEY = Fernet.generate_key()
    logger.critical(
        "FERNET_KEY is not set! Using an ephemeral key — 2FA secrets will be lost on restart. "
        "Generate a persistent key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

fernet = Fernet(FERNET_KEY)


def generate_totp_secret():
    return pyotp.random_base32()

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(secret: str) -> str:
    return fernet.decrypt(secret.encode()).decode()

def generate_qr_uri(email: str, secret: str, issuer="Apter Financial"):
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)

def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def generate_backup_codes(count=10):
    codes = []
    hashed = []
    for _ in range(count):
        raw = secrets.token_hex(4)
        codes.append(raw)
        hashed.append(hashlib.sha256(raw.encode()).hexdigest())
    return codes, hashed

def verify_backup_code(input_code, stored_hashes):
    hashed = hashlib.sha256(input_code.encode()).hexdigest()
    if hashed in stored_hashes:
        stored_hashes.remove(hashed)
        return True, stored_hashes
    return False, stored_hashes
