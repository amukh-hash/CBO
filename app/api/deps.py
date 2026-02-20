from __future__ import annotations

from datetime import UTC, datetime
from typing import Generator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.db.models import Session as UserSession
from app.db.models import User
from app.core.security import SecurityManager


security = SecurityManager()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("cb_session")
    if not token:
        raise HTTPException(status_code=401)
    token_hash = security.hash_token(token)
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if not sess:
        raise HTTPException(status_code=401)
    expiry = sess.expires_at if sess.expires_at.tzinfo is None else sess.expires_at.astimezone(UTC).replace(tzinfo=None)
    if expiry < datetime.now(UTC).replace(tzinfo=None):
        raise HTTPException(status_code=401)
    user = db.get(User, sess.user_id)
    if not user:
        raise HTTPException(status_code=401)
    return user
