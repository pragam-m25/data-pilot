import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from jose import jwt
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet_key() -> bytes:
    # Derive a valid 32-byte URL-safe base64 Fernet key from the config key
    key_bytes = settings.ENCRYPTION_KEY.encode()
    hash_32 = hashlib.sha256(key_bytes).digest()
    return base64.urlsafe_b64encode(hash_32)

_fernet = Fernet(_get_fernet_key())

def encrypt_secret(secret_text: str) -> str:
    """Encrypt sensitive string (e.g. database password/URI) using AES-256 Fernet."""
    if not secret_text:
        return ""
    return _fernet.encrypt(secret_text.encode()).decode()

def decrypt_secret(encrypted_text: str) -> str:
    """Decrypt sensitive string."""
    if not encrypted_text:
        return ""
    try:
        return _fernet.decrypt(encrypted_text.encode()).decode()
    except Exception:
        return ""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against SHA256 with salt."""
    if not hashed_password or ":" not in hashed_password:
        return False
    salt, hash_val = hashed_password.split(":", 1)
    test_hash = hashlib.sha256((salt + plain_password).encode()).hexdigest()
    return test_hash == hash_val

def get_password_hash(password: str) -> str:
    """Generate salted SHA256 password hash."""
    salt = hashlib.sha256(str(datetime.now(timezone.utc).timestamp()).encode()).hexdigest()[:16]
    hash_val = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hash_val}"

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None
