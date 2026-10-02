import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

_hasher = PasswordHasher()  # Argon2id


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


# --- TOTP (2FA opzionale) -----------------------------------------------------------
def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="FeedTrace")


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


# --- limitazione tentativi di login (in memoria; hardening completo in F7) -----------
_failures: dict[str, list[float]] = {}


def login_blocked(key: str) -> bool:
    cutoff = time.monotonic() - settings.login_window_seconds
    recent = [t for t in _failures.get(key, []) if t > cutoff]
    _failures[key] = recent
    return len(recent) >= settings.login_max_failures


def register_login_failure(key: str) -> None:
    _failures.setdefault(key, []).append(time.monotonic())


def reset_login_failures(key: str) -> None:
    _failures.pop(key, None)
