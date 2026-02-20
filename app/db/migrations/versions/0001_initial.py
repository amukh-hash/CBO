"""initial schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("csrf_token", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "auth_factors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("factor_type", sa.String(length=32), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("recovery_codes_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False, unique=True),
    )

    op.create_table(
        "insurance_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("adapter_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("circuit_failures", sa.Integer(), nullable=False),
    )

    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("insurance_providers.id"), nullable=False),
        sa.Column("plan_type", sa.String(length=16), nullable=False),
        sa.Column("policy_number_enc", sa.Text(), nullable=False),
        sa.Column("group_number", sa.String(length=128), nullable=True),
        sa.Column("deductible_cents", sa.Integer(), nullable=False),
        sa.Column("oop_max_cents", sa.Integer(), nullable=False),
    )

    op.create_table(
        "policy_coverage_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("policies.id"), nullable=False),
        sa.Column("network_tier", sa.String(length=32), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("deductible_cents", sa.Integer(), nullable=False),
        sa.Column("oop_max_cents", sa.Integer(), nullable=False),
    )

    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("policies.id"), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("dob_enc", sa.Text(), nullable=False),
        sa.Column("member_id_enc", sa.Text(), nullable=False),
        sa.Column("relationship", sa.String(length=64), nullable=False),
    )

    op.create_table(
        "service_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("provider_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("total_billed_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_event_id", sa.Integer(), sa.ForeignKey("service_events.id"), nullable=False),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("policies.id"), nullable=False),
        sa.Column("claim_status", sa.String(length=16), nullable=False),
        sa.Column("insurer_claim_id_enc", sa.Text(), nullable=False),
        sa.Column("allowed_amount_cents", sa.Integer(), nullable=False),
        sa.Column("paid_amount_cents", sa.Integer(), nullable=False),
    )

    op.create_table(
        "eobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("issued_date", sa.Date(), nullable=False),
        sa.Column("patient_responsibility_cents", sa.Integer(), nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=False),
    )

    op.create_table(
        "expense_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_event_id", sa.Integer(), sa.ForeignKey("service_events.id"), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("incurred_at", sa.Date(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("reconciled", sa.Boolean(), nullable=False),
    )
    op.create_unique_constraint("uq_expense_idempotency_key", "expense_line_items", ["idempotency_key"])

    op.create_table(
        "patient_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expense_id", sa.Integer(), sa.ForeignKey("expense_line_items.id"), nullable=False),
        sa.Column("paid_at", sa.Date(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("last4", sa.String(length=4), nullable=True),
    )

    op.create_table(
        "account_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("color", sa.String(length=16), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("doc_type", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False, unique=True),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column("sha256_plaintext", sa.String(length=64), nullable=False),
        sa.Column("sha256_ciphertext", sa.String(length=64), nullable=False),
        sa.Column("aad_sha256", sa.String(length=64), nullable=False),
        sa.Column("encryption_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for name in [
        "documents",
        "account_tags",
        "patient_payments",
        "expense_line_items",
        "eobs",
        "claims",
        "service_events",
        "members",
        "policy_coverage_terms",
        "policies",
        "insurance_providers",
        "audit_events",
        "auth_factors",
        "sessions",
        "users",
    ]:
        op.drop_table(name)
