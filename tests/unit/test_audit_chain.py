from app.core.audit import write_audit_event
from app.core.integrity import verify_audit_chain
from app.db.base import Base, engine, db_session


def test_audit_hash_chain_continuity() -> None:
    Base.metadata.create_all(bind=engine)
    with db_session() as db:
        write_audit_event(db, "create", "x", "1", None, {"a": 1})
        write_audit_event(db, "update", "x", "1", None, {"b": 2})
    with db_session() as db:
        assert verify_audit_chain(db) == []
