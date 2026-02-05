import pyotp
import secrets
import hashlib
from cryptography.fernet import Fernet

FERNET_KEY = Fernet.generate_key()
fernet = Fernet(FERNET_KEY)

def generate_totp_secret():
    return pyotp.random_base32()

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(secret: str) -> str:
    return fernet.decrypt(secret.encode()).decode()

def generate_qr_uri(email: str, secret: str, issuer="BotTrader"):
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
