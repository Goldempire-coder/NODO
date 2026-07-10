from __future__ import annotations

from email.parser import BytesParser
from email.policy import default

from fastapi import APIRouter, Depends, Header, Request

from app.auth.dependencies import require_current_user
from app.core.errors import ApiError
from app.modules.businesses.route_dependencies import legacy_onboarding_service, request_id, require_test_fixture_business_endpoint
from app.modules.businesses.schemas import BusinessCreateRequest, BusinessUpdateRequest, BusinessVerificationSubmitRequest
from app.modules.users.models import UserRecord

router = APIRouter(tags=["businesses-legacy"])


def _parse_multipart(content_type: str, body: bytes) -> tuple[str, str, str, bytes]:
    if not content_type.startswith("multipart/form-data"):
        raise ApiError("BUSINESS_DOCUMENT_INVALID", status_code=400)
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    file_type = ""
    file_name = "document.bin"
    mime_type = "application/octet-stream"
    content = b""
    for part in message.iter_parts():
        disposition = part.get("Content-Disposition", "")
        name = part.get_param("name", header="content-disposition")
        if name == "file_type":
            file_type = part.get_content().strip()
        elif name == "file":
            file_name = part.get_filename() or file_name
            mime_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            content = payload or b""
        elif "form-data" not in disposition:
            continue
    if not file_type or not content:
        raise ApiError("BUSINESS_DOCUMENT_INVALID", status_code=400)
    return file_type, file_name, mime_type, content


@router.post("/businesses", status_code=201)
def create_business(
    payload: BusinessCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_test_fixture_business_endpoint(request)
    data = legacy_onboarding_service(request).create_business(
        user=user,
        payload=payload,
        request_id=request_id(request),
        idempotency_key=idempotency_key,
    )
    return {"data": data, "request_id": request_id(request)}


@router.put("/businesses/{business_id}")
def update_business(
    business_id: str,
    payload: BusinessUpdateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_test_fixture_business_endpoint(request)
    data = legacy_onboarding_service(request).update_business(
        user=user,
        business_id=business_id,
        payload=payload,
        request_id=request_id(request),
        idempotency_key=idempotency_key,
    )
    return {"data": data, "request_id": request_id(request)}


@router.post("/businesses/{business_id}/verification-documents", status_code=201)
async def upload_verification_document(
    business_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    require_test_fixture_business_endpoint(request)
    file_type, file_name, mime_type, content = _parse_multipart(request.headers.get("content-type", ""), await request.body())
    data = legacy_onboarding_service(request).upload_document(
        user=user,
        business_id=business_id,
        file_type=file_type,
        file_name=file_name,
        mime_type=mime_type,
        content=content,
        request_id=request_id(request),
    )
    return {"data": data, "request_id": request_id(request)}


@router.post("/businesses/{business_id}/submit-verification")
def submit_verification(
    business_id: str,
    payload: BusinessVerificationSubmitRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_test_fixture_business_endpoint(request)
    data = legacy_onboarding_service(request).submit_verification(
        user=user,
        business_id=business_id,
        payload=payload,
        request_id=request_id(request),
        idempotency_key=idempotency_key,
    )
    return {"data": data, "request_id": request_id(request)}
