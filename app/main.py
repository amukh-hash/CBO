from __future__ import annotations

import os
import webbrowser
from urllib.parse import urlparse
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import (
    routes_auth,
    routes_dashboard,
    routes_expenses,
    routes_exports,
    routes_policies,
    routes_providers,
    routes_system_health,
)
from app.core.backups import BackupManager
from app.core.config import get_settings
from app.core.crypto import KeyManager
from app.core.integrity import verify_audit_chain, verify_document_hashes
from app.core.keystore import KeystoreError
from app.core.logging import get_logger
from app.core.security import SecurityManager, require_csrf_async, set_csrf_cookie
from app.db.base import Base, db_session, engine, ensure_runtime_schema
from app.db.models import User

logger = get_logger()
settings = get_settings()
security = SecurityManager()


def csrf_context_processor(request: Request) -> dict[str, str]:
    token = getattr(request.state, "csrf_token", None) or request.cookies.get("cb_csrf", "")
    return {"csrf_token": token}

app = FastAPI(title="CB Organizer")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "ui" / "static")), name="static")
templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "ui" / "templates"),
    context_processors=[csrf_context_processor],
)

routes_auth.register_templates(templates)
routes_dashboard.register_templates(templates)
routes_providers.register_templates(templates)
routes_policies.register_templates(templates)
routes_expenses.register_templates(templates)
routes_system_health.register_templates(templates)

app.include_router(routes_auth.router)
app.include_router(routes_dashboard.router)
app.include_router(routes_providers.router)
app.include_router(routes_policies.router)
app.include_router(routes_expenses.router)
app.include_router(routes_exports.router)
app.include_router(routes_system_health.router)

scheduler = BackgroundScheduler()


@app.middleware("http")
async def csrf_middleware(request: Request, call_next) -> Response:
    cookie_token = request.cookies.get("cb_csrf")
    request.state.csrf_token = cookie_token or security.new_csrf_token()

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        try:
            await require_csrf_async(request)
        except HTTPException as exc:
            accept = request.headers.get("accept", "")
            if "text/html" in accept:
                referer = request.headers.get("referer")
                target = "/auth/login?error=csrf"
                if referer:
                    parsed = urlparse(referer)
                    if parsed.path and parsed.path != request.url.path:
                        target = parsed.path
                        if parsed.query:
                            target = f"{target}?{parsed.query}"
                    elif parsed.path and parsed.path != "/":
                        target = parsed.path
                elif not request.url.path.startswith("/auth"):
                    target = "/"
                response = RedirectResponse(target, status_code=303)
                set_csrf_cookie(response, security.new_csrf_token())
                return response

            response = PlainTextResponse(exc.detail, status_code=exc.status_code)
            if not cookie_token:
                set_csrf_cookie(response, request.state.csrf_token)
            return response

    response = await call_next(request)
    if not cookie_token:
        set_csrf_cookie(response, request.state.csrf_token)
    return response


@app.exception_handler(KeystoreError)
async def keystore_error_handler(request: Request, exc: KeystoreError) -> PlainTextResponse:
    logger.warning("Vault unlock failed at path %s: %s", request.url.path, str(exc))
    return PlainTextResponse("Vault is locked. Configure your vault passphrase and try again.", status_code=400)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    if exc.status_code == 401:
        accepts_html = "text/html" in (request.headers.get("accept", ""))
        if accepts_html and not request.url.path.startswith("/auth"):
            return RedirectResponse("/auth/login", status_code=303)
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return PlainTextResponse(detail, status_code=exc.status_code)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    backup_manager = BackupManager(settings)
    default_pin = "1224"

    with db_session() as db:
        existing_user = db.query(User).order_by(User.id.asc()).first()
        if not existing_user:
            db.add(
                User(
                    email="local-user",
                    password_hash=security.hash_password(default_pin),
                    mfa_enabled=False,
                )
            )
            logger.info("Created default local user with default PIN.")
        else:
            existing_user.email = "local-user"
            existing_user.password_hash = security.hash_password(default_pin)
            logger.info("Reset single-user PIN to configured default.")

    if not os.getenv("CB_ORGANIZER_PASSPHRASE"):
        os.environ["CB_ORGANIZER_PASSPHRASE"] = default_pin
    km = KeyManager(passphrase=os.getenv("CB_ORGANIZER_PASSPHRASE"))
    if km.keystore.load() is None:
        km.get_or_create_kek()
    
    def docs_integrity_job() -> None:
        with db_session() as db:
            verify_document_hashes(db, settings.docs_dir)

    def audit_integrity_job() -> None:
        with db_session() as db:
            verify_audit_chain(db)

    scheduler.add_job(backup_manager.create_backup, "cron", hour=2, minute=0, id="nightly_backup", replace_existing=True)
    scheduler.add_job(docs_integrity_job, "interval", hours=6, id="integrity_docs", replace_existing=True)
    scheduler.add_job(audit_integrity_job, "interval", hours=6, id="integrity_audit", replace_existing=True)
    scheduler.start()
    logger.info("Application started")


@app.on_event("shutdown")
def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def open_browser() -> None:
    webbrowser.open(f"http://{settings.host}:{settings.port}")
