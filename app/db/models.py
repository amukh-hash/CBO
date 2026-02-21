from __future__ import annotations

from datetime import UTC, datetime, date

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import ClaimStatus, DocumentType, NetworkTier, PlanType, ProviderAdapterType


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # PHI classification: PII (email)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AuthFactor(Base):
    __tablename__ = "auth_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    factor_type: Mapped[str] = mapped_column(String(32), default="totp")
    # PHI classification: sensitive secret (encrypted)
    secret_encrypted: Mapped[str] = mapped_column(Text)
    # PHI classification: sensitive recovery codes (encrypted)
    recovery_codes_encrypted: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)


class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # PHI classification: provider/practice name (may contain PHI context)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    # PHI classification: provider specialty
    specialty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # PHI classification: non-sensitive UI selection color
    selector_color: Mapped[str] = mapped_column(String(7), default="#7B1FA2")
    # PHI classification: estimated payment amount
    estimated_copay_cents: Mapped[int] = mapped_column(Integer, default=0)
    # PHI classification: free-form notes (may contain PHI)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    adapter_type: Mapped[ProviderAdapterType] = mapped_column(Enum(ProviderAdapterType))
    status: Mapped[str] = mapped_column(String(32), default="active")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    circuit_failures: Mapped[int] = mapped_column(Integer, default=0)


class ProviderAddress(Base):
    __tablename__ = "provider_addresses"
    __table_args__ = (UniqueConstraint("provider_id", "address_text", name="uq_provider_addresses_provider_text"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("insurance_providers.id"), index=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # PHI classification: provider location details
    address_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("insurance_providers.id"), index=True)
    plan_type: Mapped[PlanType] = mapped_column(Enum(PlanType))
    # PHI classification: sensitive policy identifier (encrypted)
    policy_number_enc: Mapped[str] = mapped_column(Text)
    group_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    monthly_premium_cents: Mapped[int] = mapped_column(Integer, default=0)
    deductible_cents: Mapped[int] = mapped_column(Integer, default=0)
    oop_max_cents: Mapped[int] = mapped_column(Integer, default=0)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("insurance_providers.id"), index=True)
    # PHI classification: appointment timestamp and schedule metadata
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    estimated_invoice_cents: Mapped[int] = mapped_column(Integer, default=0)
    # PHI classification: location/facility details
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # PHI classification: facility address
    facility_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # PHI classification: free-form preparation notes
    prep_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # PHI classification: appointment notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PolicyCoverageTerm(Base):
    __tablename__ = "policy_coverage_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), index=True)
    network_tier: Mapped[NetworkTier] = mapped_column(Enum(NetworkTier))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deductible_cents: Mapped[int] = mapped_column(Integer, default=0)
    oop_max_cents: Mapped[int] = mapped_column(Integer, default=0)


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), index=True)
    # PHI classification: PII (name)
    full_name: Mapped[str] = mapped_column(String(255))
    # PHI classification: PHI (DOB encrypted)
    dob_enc: Mapped[str] = mapped_column(Text)
    # PHI classification: PHI identifier (encrypted)
    member_id_enc: Mapped[str] = mapped_column(Text)
    relationship: Mapped[str] = mapped_column(String(64), default="self")


class ServiceEvent(Base):
    __tablename__ = "service_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    service_date: Mapped[date] = mapped_column(Date)
    provider_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    total_billed_cents: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="new")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_event_id: Mapped[int] = mapped_column(ForeignKey("service_events.id"), index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), index=True)
    claim_status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus), default=ClaimStatus.SUBMITTED)
    # PHI classification: insurer claim identifier (encrypted)
    insurer_claim_id_enc: Mapped[str] = mapped_column(Text)
    allowed_amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    paid_amount_cents: Mapped[int] = mapped_column(Integer, default=0)


class EOB(Base):
    __tablename__ = "eobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    issued_date: Mapped[date] = mapped_column(Date)
    patient_responsibility_cents: Mapped[int] = mapped_column(Integer, default=0)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ExpenseLineItem(Base):
    __tablename__ = "expense_line_items"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_expense_idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_event_id: Mapped[int | None] = mapped_column(ForeignKey("service_events.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(128), default="medical")
    amount_cents: Mapped[int] = mapped_column(Integer)
    incurred_at: Mapped[date] = mapped_column(Date)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)


class PatientPayment(Base):
    __tablename__ = "patient_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expense_line_items.id"), index=True)
    paid_at: Mapped[date] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(64))
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)


class AccountTag(Base):
    __tablename__ = "account_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="#000000")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    policy_id: Mapped[int | None] = mapped_column(ForeignKey("policies.id"), index=True, nullable=True)
    expense_id: Mapped[int | None] = mapped_column(ForeignKey("expense_line_items.id"), index=True, nullable=True)
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), default=DocumentType.RECEIPT)
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(512), unique=True)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary)
    sha256_plaintext: Mapped[str] = mapped_column(String(64), index=True)
    sha256_ciphertext: Mapped[str] = mapped_column(String(64), index=True)
    aad_sha256: Mapped[str] = mapped_column(String(64), index=True, default="")
    encryption_version: Mapped[int] = mapped_column(Integer, default=1)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
