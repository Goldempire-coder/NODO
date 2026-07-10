from __future__ import annotations

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord, BusinessVerificationSubmissionRecord


OWNER_UPDATE_ALLOWED = {"pending", "rejected", "approved", "suspended"}
OWNER_UPLOAD_ALLOWED = {"pending", "rejected"}
OWNER_SUBMIT_ALLOWED = {"pending", "rejected"}


def require_owner_update_allowed(business: BusinessRecord) -> None:
    if business.verification_status not in OWNER_UPDATE_ALLOWED:
        raise ApiError("BUSINESS_STATUS_INVALID", status_code=409)


def require_owner_upload_allowed(business: BusinessRecord) -> None:
    if business.verification_status not in OWNER_UPLOAD_ALLOWED:
        raise ApiError("BUSINESS_STATUS_INVALID", status_code=409)


def require_owner_submit_allowed(business: BusinessRecord) -> None:
    if business.verification_status not in OWNER_SUBMIT_ALLOWED:
        raise ApiError("BUSINESS_STATUS_INVALID", status_code=409)


def require_admin_review_allowed(
    business: BusinessRecord,
    latest_submission: BusinessVerificationSubmissionRecord | None,
) -> BusinessVerificationSubmissionRecord:
    if business.verification_status != "pending":
        raise ApiError("BUSINESS_STATUS_INVALID", status_code=409)
    if latest_submission is None or latest_submission.status != "pending":
        raise ApiError("BUSINESS_STATUS_INVALID", status_code=409)
    return latest_submission
