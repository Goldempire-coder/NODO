from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.orders.models import OrderRecord

TRC20_TRANSACTION_HASH_PATTERN = re.compile(r"^(?:0x)?([a-f0-9]{64})$")
PAYMENT_PROOF_CONTENT_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class AtomicCancellationResult:
    order: OrderRecord
    ad_requires_expiration: bool
    capacity_released: bool


def canonical_network(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized or None


def canonical_transaction_hash(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    match = TRC20_TRANSACTION_HASH_PATTERN.fullmatch(normalized)
    if not match:
        raise ValueError("tx_hash must be 64 hexadecimal characters with optional 0x prefix")
    return match.group(1)
