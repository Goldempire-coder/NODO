from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeDocumentRecord, BusinessIntakeRequestRecord


REQUIRED_INTAKE_FIELDS: tuple[tuple[str, str], ...] = (
    ("referral_code", "codigo de referencia"),
    ("contact_phone", "WhatsApp"),
    ("business_name", "nombre del negocio"),
    ("business_tax_id", "RIF del negocio"),
    ("responsible_name", "responsable"),
    ("responsible_id_number", "cedula del responsable"),
    ("business_phone", "telefono del negocio"),
    ("min_amount_usd", "monto minimo"),
    ("max_amount_usd", "monto maximo"),
    ("daily_limit_usd", "limite diario"),
    ("references_json", "redes sociales"),
)


def missing_required_intake_fields(
    intake: BusinessIntakeRequestRecord,
    *,
    documents: Sequence[BusinessIntakeDocumentRecord],
) -> list[str]:
    return missing_required_intake_field_labels(intake, document_count=len(documents))


def missing_required_intake_field_labels(
    intake: BusinessIntakeRequestRecord,
    *,
    document_count: int,
) -> list[str]:
    missing: list[str] = []
    for field_name, label in REQUIRED_INTAKE_FIELDS:
        value: Any = getattr(intake, field_name)
        if value is None or value == "" or value == []:
            missing.append(label)
    if document_count <= 0:
        missing.append("documentos")
    return missing


def intake_review_metadata(intake: BusinessIntakeRequestRecord, *, document_count: int) -> tuple[bool, int]:
    missing = missing_required_intake_field_labels(intake, document_count=document_count)
    return len(missing) == 0, len(missing)


def ensure_intake_ready_for_review(
    intake: BusinessIntakeRequestRecord,
    *,
    documents: Sequence[BusinessIntakeDocumentRecord],
    error_code: str = "BUSINESS_INTAKE_INCOMPLETE",
    status_code: int = 409,
) -> None:
    missing = missing_required_intake_fields(intake, documents=documents)
    if missing:
        raise ApiError(
            error_code,
            status_code=status_code,
            message=f"La solicitud no tiene informacion suficiente para aprobar el negocio. Falta: {', '.join(missing)}.",
        )
