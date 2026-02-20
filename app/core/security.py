from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs
from typing import Optional

import pyotp
from argon2 import PasswordHasher
from fastapi import HTTPException, Request, Response

from app.core.config import get_settings
from app.core.crypto import FieldEncryptor

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
settings = get_settings()


class SecurityManager:
    def __init__(self) -> None:
        self.field_encryptor = FieldEncryptor()

    def hash_password(self, password: str) -> str:
        return password_hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return password_hasher.verify(password_hash, password)
        except Exception:
            return False

    def new_session_token(self) -> str:
        return secrets.token_urlsafe(48)

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def new_csrf_token(self) -> str:
        return secrets.token_urlsafe(32)

    def set_session_cookie(self, response: Response, token: str) -> None:
        cookie_secure = settings.lan_https_mode and not settings.localhost_only
        response.set_cookie(
            key="cb_session",
            value=token,
            httponly=True,
            secure=cookie_secure,
            samesite="lax",
            max_age=int(timedelta(days=14).total_seconds()),
        )

    def clear_session_cookie(self, response: Response) -> None:
        response.delete_cookie("cb_session")

    def session_expiry(self) -> datetime:
        return datetime.now(UTC) + timedelta(days=14)

    def create_totp_secret(self) -> str:
        return pyotp.random_base32()

    def totp_uri(self, user_email: str, secret: str) -> str:
        return pyotp.totp.TOTP(secret).provisioning_uri(name=user_email, issuer_name="CB Organizer")

    def verify_totp(self, secret: str, code: str) -> bool:
        return pyotp.TOTP(secret).verify(code, valid_window=1)

    def generate_recovery_codes(self, count: int = 8) -> list[str]:
        return [secrets.token_hex(4) for _ in range(count)]

    def hash_recovery_code(self, code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def hash_recovery_codes(self, codes: list[str]) -> list[str]:
        return [self.hash_recovery_code(code) for code in codes]


def require_csrf(request: Request) -> None:
    raise RuntimeError("Use require_csrf_async in async request handling.")


async def require_csrf_async(request: Request) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    form_token = request.headers.get("x-csrf-token") or request.query_params.get("csrf_token")
    if not form_token:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            try:
                body = await request.body()
                parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
                token_values = parsed.get("csrf_token")
                if token_values:
                    form_token = token_values[0]
            except Exception:
                form_token = None

    cookie_token = request.cookies.get("cb_csrf")
    if not form_token or not cookie_token or not secrets.compare_digest(form_token, cookie_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def set_csrf_cookie(response: Response, token: Optional[str] = None) -> str:
    csrf = token or secrets.token_urlsafe(24)
    cookie_secure = settings.lan_https_mode and not settings.localhost_only
    response.set_cookie("cb_csrf", csrf, httponly=False, secure=cookie_secure, samesite="lax")
    return csrf


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
