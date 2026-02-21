from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})


@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def _sqlite_columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {str(row[1]) for row in rows}


def ensure_runtime_schema() -> None:
    """Apply additive schema updates for local appliance upgrades."""
    with engine.begin() as conn:
        provider_cols = _sqlite_columns(conn, "insurance_providers")
        if "specialty" not in provider_cols:
            conn.execute(text("ALTER TABLE insurance_providers ADD COLUMN specialty VARCHAR(255)"))
        if "selector_color" not in provider_cols:
            conn.execute(text("ALTER TABLE insurance_providers ADD COLUMN selector_color VARCHAR(7) NOT NULL DEFAULT '#7B1FA2'"))
        if "estimated_copay_cents" not in provider_cols:
            conn.execute(text("ALTER TABLE insurance_providers ADD COLUMN estimated_copay_cents INTEGER NOT NULL DEFAULT 0"))
        if "notes" not in provider_cols:
            conn.execute(text("ALTER TABLE insurance_providers ADD COLUMN notes TEXT"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS provider_addresses (
                    id INTEGER PRIMARY KEY,
                    provider_id INTEGER NOT NULL,
                    label VARCHAR(128),
                    address_text TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(provider_id) REFERENCES insurance_providers(id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_provider_addresses_provider_id ON provider_addresses(provider_id)"))
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_addresses_provider_text
                ON provider_addresses(provider_id, address_text)
                """
            )
        )

        policy_cols = _sqlite_columns(conn, "policies")
        if "monthly_premium_cents" not in policy_cols:
            conn.execute(text("ALTER TABLE policies ADD COLUMN monthly_premium_cents INTEGER NOT NULL DEFAULT 0"))

        expense_cols = _sqlite_columns(conn, "expense_line_items")
        if "category" not in expense_cols:
            conn.execute(text("ALTER TABLE expense_line_items ADD COLUMN category VARCHAR(128) NOT NULL DEFAULT 'medical'"))
        if "idempotency_key" not in expense_cols:
            conn.execute(text("ALTER TABLE expense_line_items ADD COLUMN idempotency_key VARCHAR(128)"))
        if "reconciled" not in expense_cols:
            conn.execute(text("ALTER TABLE expense_line_items ADD COLUMN reconciled BOOLEAN NOT NULL DEFAULT 0"))
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_expense_idempotency_key
                ON expense_line_items(idempotency_key)
                """
            )
        )

        document_cols = _sqlite_columns(conn, "documents")
        if "policy_id" not in document_cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN policy_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_policy_id ON documents(policy_id)"))
        if "expense_id" not in document_cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN expense_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_expense_id ON documents(expense_id)"))

        appointment_cols = _sqlite_columns(conn, "appointments")
        if appointment_cols:
            if "location_name" not in appointment_cols:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN location_name VARCHAR(255)"))
            if "facility_address" not in appointment_cols:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN facility_address TEXT"))
            if "prep_notes" not in appointment_cols:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN prep_notes TEXT"))
            if "notes" not in appointment_cols:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN notes TEXT"))
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE appointments (
                        id INTEGER PRIMARY KEY,
                        provider_id INTEGER NOT NULL,
                        scheduled_at DATETIME NOT NULL,
                        estimated_invoice_cents INTEGER NOT NULL DEFAULT 0,
                        location_name VARCHAR(255),
                        facility_address TEXT,
                        prep_notes TEXT,
                        notes TEXT,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(provider_id) REFERENCES insurance_providers(id)
                    )
                    """
                )
            )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_appointments_provider_id ON appointments(provider_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_appointments_scheduled_at ON appointments(scheduled_at)"))


@contextmanager
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
