from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_value, digest_value = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = _b64decode(salt_value)
        expected = _b64decode(digest_value)
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: str, organization_id: str, role: str) -> str:
    settings = get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET is not configured")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64encode(json.dumps(header, separators=(",", ":")).encode()),
            _b64encode(json.dumps(payload, separators=(",", ":")).encode()),
        ]
    )
    signature = hmac.new(
        settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.jwt_secret:
        raise ValueError("JWT secret is not configured")
    try:
        header_value, payload_value, signature_value = token.split(".")
        signing_input = f"{header_value}.{payload_value}"
        expected = hmac.new(
            settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _b64decode(signature_value)):
            raise ValueError("Invalid token signature")
        payload = json.loads(_b64decode(payload_value))
        if int(payload.get("exp", 0)) <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expired")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid access token") from exc


def encrypt_secret(secret: str) -> str:
    return Fernet(get_settings().fernet_key).encrypt(secret.encode()).decode()


def decrypt_secret(encrypted: str | None) -> str | None:
    if not encrypted:
        return None
    try:
        return Fernet(get_settings().fernet_key).decrypt(encrypted.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Stored integration secret cannot be decrypted") from exc

