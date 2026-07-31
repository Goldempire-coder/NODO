from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.models import OrderReceiverDetailsRecord


PAGO_MOVIL_BANKS = {
    "0102": "Banco de Venezuela",
    "0105": "Mercantil Banco",
    "0108": "BBVA Provincial",
    "0114": "Bancaribe",
    "0115": "Banco Exterior",
    "0128": "Banco Caroni",
    "0134": "Banesco",
    "0137": "Banco Sofitasa",
    "0138": "Banco Plaza",
    "0151": "Banco Fondo Comun",
    "0156": "100% Banco",
    "0157": "DelSur Banco Universal",
    "0163": "Banco del Tesoro",
    "0166": "Banco Agricola de Venezuela",
    "0168": "Bancrecer",
    "0169": "Mi Banco",
    "0171": "Banco Activo",
    "0172": "Bancamiga",
    "0174": "Banplus",
    "0175": "Banco Bicentenario",
    "0177": "Banfanb",
    "0191": "Banco Nacional de Credito",
}
PHONE_PATTERN = re.compile(r"^\+58\d{10}$")
DOCUMENT_PATTERN = re.compile(r"^[VEJGP]\d{6,10}$")
UNSAFE_HOLDER_PATTERN = re.compile(r"[<>\x00-\x1f\x7f]")


def normalize_bank(value: str) -> str:
    normalized = value.strip()
    if normalized not in PAGO_MOVIL_BANKS:
        raise ValueError("bank must be a supported Pago Movil bank code")
    return normalized


def normalize_phone(value: str) -> str:
    normalized = re.sub(r"[\s()-]", "", value)
    if not PHONE_PATTERN.fullmatch(normalized):
        raise ValueError("phone must use canonical +58 format")
    return normalized


def normalize_document(value: str) -> str:
    normalized = re.sub(r"[\s.\-]", "", value).upper()
    if not DOCUMENT_PATTERN.fullmatch(normalized):
        raise ValueError("document format is invalid")
    return normalized


def normalize_holder(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) < 2 or len(normalized) > 120 or UNSAFE_HOLDER_PATTERN.search(normalized):
        raise ValueError("holder format is invalid")
    return normalized


def receiver_payload_hash(payload: dict[str, str]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def masked_receiver_details(record: OrderReceiverDetailsRecord) -> dict[str, Any]:
    holder_masked = " ".join(f"{part[0]}***" for part in record.holder.split() if part)
    return {
        "bank": PAGO_MOVIL_BANKS[record.bank_code],
        "phone": f"+58*******{record.phone[-3:]}",
        "document": f"{record.document[0]}***{record.document[-3:]}",
        "holder": holder_masked,
    }


def receiver_details_created_payload(record: OrderReceiverDetailsRecord) -> dict[str, Any]:
    return {
        "order_id": record.order_id,
        "status": "shared",
        "shared_at": record.shared_at.isoformat(),
        "receiver_details_masked": masked_receiver_details(record),
    }


def receiver_details_reveal_payload(record: OrderReceiverDetailsRecord) -> dict[str, Any]:
    return {
        "order_id": record.order_id,
        "bank": PAGO_MOVIL_BANKS[record.bank_code],
        "phone": record.phone,
        "document": record.document,
        "holder": record.holder,
        "shared_at": record.shared_at.isoformat(),
    }


def require_receiver_details(record: OrderReceiverDetailsRecord | None) -> OrderReceiverDetailsRecord:
    if record is None:
        raise ApiError("ORDER_RECEIVER_DETAILS_REQUIRED", status_code=409)
    return record
