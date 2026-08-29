from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_current_user_with_terms
from app.modules.legal.schemas import BusinessLegalAcceptanceRequest
from app.modules.legal.service import BusinessLegalService
from app.modules.users.models import UserRecord

router = APIRouter(tags=["business_legal"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _surface(request: Request) -> str:
    return getattr(request.state, "surface", None) or request.headers.get("x-nodo-surface", "business_mini_app")


def _service(request: Request) -> BusinessLegalService:
    return BusinessLegalService(
        business_repository=request.app.state.business_repository,
        legal_acceptance_repository=request.app.state.business_legal_acceptance_repository,
        audit_writer=request.app.state.audit_writer,
    )


@router.get("/business/legal/requirements")
def business_legal_requirements(
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {"data": _service(request).requirements(user=user), "request_id": _request_id(request)}


@router.post("/business/legal/acceptances")
def accept_business_legal_terms(
    payload: BusinessLegalAcceptanceRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {
        "data": _service(request).accept(
            user=user,
            payload=payload,
            request_id=_request_id(request),
            surface=_surface(request),
        ),
        "request_id": _request_id(request),
    }
