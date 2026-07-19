from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeDocumentRecord, BusinessIntakeRequestRecord


REQUIRED_INTAKE_FIELDS: tuple[tuple[str, str], ...] = (
    ("referral_code", "codigo de referencia"),
    ("contact_phone", "WhatsApp"),
    ("business_name", "nombre del negocio"),
    ("responsible_name", "responsable"),
    ("city", "ciudad"),
    ("business_phone", "telefono del negocio"),
    ("operation", "operacion"),
    ("banks_json", "bancos"),
    ("methods_json", "metodos"),
    ("min_amount_usd", "monto minimo"),
    ("max_amount_usd", "monto maximo"),
    ("schedule_text", "horario"),
    ("references_json", "referencias"),
)


def missing_required_intake_fields(
    intake: BusinessIntakeRequestRecord,
    *,
    documents: Sequence[BusinessIntakeDocumentRecord],
) -> list[str]:
    missing: list[str] = []
    for field_name, label in REQUIRED_INTAKE_FIELDS:
        value: Any = getattr(intake, field_name)
        if value is None or value == "" or value == []:
            missing.append(label)
    if not documents:
        missing.append("documentos")
    return missing


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
