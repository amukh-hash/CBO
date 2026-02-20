from __future__ import annotations

from enum import StrEnum


class ClaimStatus(StrEnum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    PAID = "paid"
    DENIED = "denied"
    APPEALED = "appealed"


class DocumentType(StrEnum):
    RECEIPT = "receipt"
    EOB = "eob"
    BILL = "bill"
    POLICY = "policy"
    OTHER = "other"


class PlanType(StrEnum):
    PPO = "ppo"
    HMO = "hmo"
    EPO = "epo"
    HDHP = "hdhp"
    POS = "pos"


class NetworkTier(StrEnum):
    IN_NETWORK = "in_network"
    OUT_NETWORK = "out_network"


class ProviderAdapterType(StrEnum):
    AGGREGATOR = "aggregator"
    PORTAL_AUTOMATION = "portal_automation"
    MANUAL = "manual"
