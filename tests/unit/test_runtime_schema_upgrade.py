from __future__ import annotations

from sqlalchemy import create_engine, text

import app.db.base as db_base
import app.db.models  # noqa: F401


def _columns_for(engine, table_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f'PRAGMA table_info({table_name})')).fetchall()
    return {str(row[1]) for row in rows}


def test_ensure_runtime_schema_upgrades_legacy_appointments_table(tmp_path, monkeypatch) -> None:
    legacy_db = tmp_path / 'legacy.db'
    legacy_engine = create_engine(f'sqlite+pysqlite:///{legacy_db}', connect_args={'check_same_thread': False})

    db_base.Base.metadata.create_all(bind=legacy_engine)
    with legacy_engine.begin() as conn:
        conn.execute(text('DROP TABLE appointments'))
        conn.execute(
            text(
                '''
                CREATE TABLE appointments (
                    id INTEGER PRIMARY KEY,
                    provider_id INTEGER NOT NULL,
                    scheduled_at DATETIME NOT NULL,
                    estimated_invoice_cents INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(provider_id) REFERENCES insurance_providers(id)
                )
                '''
            )
        )

    monkeypatch.setattr(db_base, 'engine', legacy_engine)
    db_base.ensure_runtime_schema()

    columns = _columns_for(legacy_engine, 'appointments')
    assert {'location_name', 'facility_address', 'prep_notes', 'notes'}.issubset(columns)

    legacy_engine.dispose()


def test_ensure_runtime_schema_upgrades_legacy_expenses_table(tmp_path, monkeypatch) -> None:
    legacy_db = tmp_path / 'legacy_expenses.db'
    legacy_engine = create_engine(f'sqlite+pysqlite:///{legacy_db}', connect_args={'check_same_thread': False})

    db_base.Base.metadata.create_all(bind=legacy_engine)
    with legacy_engine.begin() as conn:
        conn.execute(text('DROP TABLE expense_line_items'))
        conn.execute(
            text(
                '''
                CREATE TABLE expense_line_items (
                    id INTEGER PRIMARY KEY,
                    service_event_id INTEGER,
                    amount_cents INTEGER NOT NULL,
                    incurred_at DATE NOT NULL
                )
                '''
            )
        )

    monkeypatch.setattr(db_base, 'engine', legacy_engine)
    db_base.ensure_runtime_schema()

    columns = _columns_for(legacy_engine, 'expense_line_items')
    assert {'category', 'idempotency_key', 'reconciled'}.issubset(columns)

    legacy_engine.dispose()
