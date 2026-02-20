from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.audit import write_audit_event
from app.core.backups import BackupManager
from app.core.config import get_settings
from app.core.integrity import verify_audit_chain, verify_document_hashes

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()
backup_manager = BackupManager(settings)


def register_templates(templates: Jinja2Templates) -> None:
    @router.get("", response_class=HTMLResponse)
    def health_page(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> HTMLResponse:
        doc_failures = verify_document_hashes(db, settings.docs_dir)
        audit_failures = verify_audit_chain(db)
        backups = sorted(settings.backup_dir.glob("backup-*.cbbak"))
        return templates.TemplateResponse(
            "system_health.html",
            {
                "request": request,
                "doc_failures": doc_failures,
                "audit_failures": audit_failures,
                "backup_count": len(backups),
            },
        )

    @router.post("/backup")
    def backup_now(user=Depends(current_user), db: Session = Depends(get_db)):
        backup = backup_manager.create_backup()
        write_audit_event(db, "create", "backup", backup.name, user.id, {"path": str(backup)})
        db.commit()
        return RedirectResponse("/health", status_code=303)

    @router.post("/restore-test")
    def restore_test(user=Depends(current_user), db: Session = Depends(get_db)):
        ok = backup_manager.test_restore()
        write_audit_event(db, "restore_test", "backup", "latest", user.id, {"success": ok})
        db.commit()
        return RedirectResponse("/health", status_code=303)
