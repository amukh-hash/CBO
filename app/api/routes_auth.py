from __future__ import annotations

import os
import re

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.audit import write_audit_event
from app.core.security import SecurityManager, set_csrf_cookie
from app.db.models import Session as UserSession, User

router = APIRouter(prefix="/auth", tags=["auth"])
security = SecurityManager()
PIN_RE = re.compile(r"^\d{4}$")


def _valid_pin(pin: str) -> bool:
    return PIN_RE.fullmatch(pin) is not None


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("/login", response_class=HTMLResponse)
    def login_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("login.html", {"request": request, "error": request.query_params.get("error")})

    @router.post("/register")
    def register(
        request: Request,
        db: Session = Depends(get_db),
    ) -> Response:
        write_audit_event(db, "register_rejected", "user", "single_user_mode", None, {"reason": "disabled"})
        db.commit()
        return RedirectResponse("/auth/login?error=disabled", status_code=303)

    @router.post("/login")
    def login(
        request: Request,
        pin: str | None = Form(None),
        password: str | None = Form(None),
        db: Session = Depends(get_db),
    ) -> Response:
        resolved_pin = (pin or password or "").strip()
        if not _valid_pin(resolved_pin):
            return RedirectResponse("/auth/login?error=pin", status_code=303)

        user = db.scalar(select(User).order_by(User.id.asc()).limit(1))
        if not user or not security.verify_password(resolved_pin, user.password_hash):
            write_audit_event(db, "login_failed", "user", "local-user", None, {"reason": "invalid_credentials"})
            db.commit()
            return RedirectResponse("/auth/login?error=invalid", status_code=303)
        if not os.getenv("CB_ORGANIZER_PASSPHRASE"):
            os.environ["CB_ORGANIZER_PASSPHRASE"] = resolved_pin

        token = security.new_session_token()
        csrf = security.new_csrf_token()
        sess = UserSession(
            user_id=user.id,
            token_hash=security.hash_token(token),
            csrf_token=csrf,
            expires_at=security.session_expiry(),
        )
        db.add(sess)
        write_audit_event(db, "login", "user", str(user.id), user.id, {"name": user.email})
        db.commit()
        resp = RedirectResponse("/", status_code=303)
        security.set_session_cookie(resp, token)
        set_csrf_cookie(resp, csrf)
        return resp

    @router.post("/logout")
    def logout(request: Request, db: Session = Depends(get_db)) -> Response:
        token = request.cookies.get("cb_session")
        if token:
            token_hash = security.hash_token(token)
            sess = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
            if sess:
                write_audit_event(db, "logout", "user", str(sess.user_id), sess.user_id, {})
                db.delete(sess)
                db.commit()
        resp = RedirectResponse("/auth/login", status_code=303)
        security.clear_session_cookie(resp)
        resp.delete_cookie("cb_csrf")
        return resp
