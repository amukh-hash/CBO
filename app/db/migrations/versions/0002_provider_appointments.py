"""provider metadata, appointments, and policy-linked documents"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_provider_appointments"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("insurance_providers") as batch_op:
        batch_op.add_column(sa.Column("specialty", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("selector_color", sa.String(length=7), nullable=False, server_default="#7B1FA2"))
        batch_op.add_column(sa.Column("estimated_copay_cents", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))

    with op.batch_alter_table("policies") as batch_op:
        batch_op.add_column(sa.Column("monthly_premium_cents", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("policy_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_documents_policy_id", ["policy_id"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("insurance_providers.id"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_invoice_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("facility_address", sa.Text(), nullable=True),
        sa.Column("prep_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointments_provider_id", "appointments", ["provider_id"], unique=False)
    op.create_index("ix_appointments_scheduled_at", "appointments", ["scheduled_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_appointments_scheduled_at", table_name="appointments")
    op.drop_index("ix_appointments_provider_id", table_name="appointments")
    op.drop_table("appointments")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("ix_documents_policy_id")
        batch_op.drop_column("policy_id")

    with op.batch_alter_table("policies") as batch_op:
        batch_op.drop_column("monthly_premium_cents")

    with op.batch_alter_table("insurance_providers") as batch_op:
        batch_op.drop_column("notes")
        batch_op.drop_column("estimated_copay_cents")
        batch_op.drop_column("selector_color")
        batch_op.drop_column("specialty")
