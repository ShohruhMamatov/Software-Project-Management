"""Passwords, JWT tokens, store API keys, camera-password encryption, and the auth dependencies."""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Store, User, UserRole

JWT_ALGORITHM = "HS256"


# ---------- Passwords (bcrypt) ----------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ---------- JWT ----------

def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.jwt_secret, algorithm=JWT_ALGORITHM)


# auto_error=False so we can return 401 (not 403) when the header is missing.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: the logged-in user from `Authorization: Bearer <token>`."""
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"}
    )
    if creds is None:
        raise unauthorized
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def get_current_store(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Store:
    """Dependency: the store of the logged-in user (400 if they have not created one yet)."""
    if user.store_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Create a store first")
    return db.get(Store, user.store_id)


def require_owner(user: User = Depends(get_current_user)) -> User:
    """Dependency: only store owners may manage the store and its cameras."""
    if user.role != UserRole.owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the store owner can do this")
    return user


# ---------- Store API keys (edge agent) ----------
# The key is long and random, so a plain SHA-256 is enough (and lets us look it up directly).

def new_api_key() -> str:
    return "lumi_" + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_agent_store(x_api_key: str | None = Header(default=None), db: Session = Depends(get_db)) -> Store:
    """Dependency for edge-agent endpoints: the store that owns the `X-API-Key` header."""
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-API-Key")
    store = db.scalar(select(Store).where(Store.api_key_hash == hash_api_key(x_api_key)))
    if store is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return store


# ---------- Camera passwords (Fernet) ----------

def _fernet() -> Fernet:
    # Derive a valid 32-byte Fernet key from whatever secret string is configured.
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.camera_enc_key.encode()).digest())
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
