from __future__ import annotations

import hashlib
import time
from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.presenters import file_payload
from app.modules.orders.helpers import profile_attach, profile_enabled, profile_mark, require_uuid
from app.modules.orders.models import new_id
from app.modules.orders.payment_constants import ALLOWED_PAYMENT_EVIDENCE_MIME_TYPES, MAX_PAYMENT_EVIDENCE_SIZE_BYTES
from app.modules.orders.policy import require_order_owner, require_remitter
from app.modules.orders.state_machine import require_payment_reveal_allowed
from app.modules.users.models import UserRecord


class PaymentEvidenceMixin:
    def upload_payment_evidence(
        self,
        *,
        user: UserRecord,
        order_id: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        pending_payment_report_id: str | None,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        profile = [] if profile_enabled() else None
        profile_started = time.perf_counter()
        stage_started = time.perf_counter()
        require_remitter(user)
        self._rate_limit("payment_evidence", user)  # type: ignore[attr-defined]
        profile_mark(profile, "service:auth_and_rate_limit", stage_started)
        stage_started = time.perf_counter()
        order_id, payment_report_id = self._validate_payment_evidence_request(
            order_id=order_id,
            pending_payment_report_id=pending_payment_report_id,
            mime_type=mime_type,
            content=content,
            idempotency_key=idempotency_key,
        )
        profile_mark(profile, "service:validate_payload", stage_started)
        stage_started = time.perf_counter()
        payload = self._payment_evidence_idempotency_payload(order_id=order_id, file_name=file_name, mime_type=mime_type, content=content, payment_report_id=payment_report_id)
        profile_mark(profile, "service:payload_hash_inputs", stage_started)

        def compute() -> dict[str, Any]:
            return self._compute_payment_evidence_upload(
                user=user,
                order_id=order_id,
                file_name=file_name,
                mime_type=mime_type,
                content=content,
                payment_report_id=payment_report_id,
                request_id=request_id,
                profile=profile,
            )

        stage_started = time.perf_counter()
        response = self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"orders:payment_evidence:{user.id}:{order_id}:{idempotency_key}",
            payload=payload,
            compute=compute,
        )
        profile_mark(profile, "service:idempotency_replay_or_store", stage_started)
        return profile_attach(dict(response), profile, profile_started)

    def _validate_payment_evidence_request(
        self,
        *,
        order_id: str,
        pending_payment_report_id: str | None,
        mime_type: str,
        content: bytes,
        idempotency_key: str | None,
    ) -> tuple[str, str]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if self._storage is None:  # type: ignore[attr-defined]
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        if mime_type not in ALLOWED_PAYMENT_EVIDENCE_MIME_TYPES or not content or len(content) > MAX_PAYMENT_EVIDENCE_SIZE_BYTES:
            raise ApiError("INVALID_PAYMENT_EVIDENCE", status_code=400)
        return require_uuid(order_id, "ORDER_NOT_FOUND") or order_id, require_uuid(pending_payment_report_id, "INVALID_PAYMENT_EVIDENCE") or new_id()

    def _payment_evidence_idempotency_payload(self, *, order_id: str, file_name: str, mime_type: str, content: bytes, payment_report_id: str) -> dict[str, Any]:
        return {
            "order_id": order_id,
            "file_name": file_name,
            "mime_type": mime_type,
            "size_bytes": len(content),
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "pending_payment_report_id": payment_report_id,
        }

    def _compute_payment_evidence_upload(
        self,
        *,
        user: UserRecord,
        order_id: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        payment_report_id: str,
        request_id: str,
        profile: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        order = self._payment_evidence_order(user=user, order_id=order_id, profile=profile)
        file = self._store_payment_evidence_file(user=user, order_id=order.id, file_name=file_name, mime_type=mime_type, content=content, payment_report_id=payment_report_id, profile=profile)
        self._audit_payment_evidence_upload(user=user, order_id=order.id, file=file, payment_report_id=payment_report_id, request_id=request_id, profile=profile)
        stage_started = time.perf_counter()
        response = {"file": file_payload(file), "pending_payment_report_id": payment_report_id}
        profile_mark(profile, "service:payment_evidence_payload", stage_started)
        return response

    def _payment_evidence_order(self, *, user: UserRecord, order_id: str, profile: list[dict[str, Any]] | None):  # type: ignore[no-untyped-def]
        stage_started = time.perf_counter()
        order = self._repository.get_by_id(order_id)  # type: ignore[attr-defined]
        profile_mark(profile, "repo:get_order", stage_started)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        stage_started = time.perf_counter()
        require_order_owner(user, order)
        require_payment_reveal_allowed(order)
        profile_mark(profile, "service:ownership_and_state", stage_started)
        return order

    def _store_payment_evidence_file(
        self,
        *,
        user: UserRecord,
        order_id: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        payment_report_id: str,
        profile: list[dict[str, Any]] | None,
    ):  # type: ignore[no-untyped-def]
        content_sha256 = hashlib.sha256(content).hexdigest()
        stage_started = time.perf_counter()
        file_id = new_id()
        stored = self._storage.store_payment_evidence(order_id=order_id, payment_report_id=payment_report_id, file_id=file_id, file_name=file_name, content=content)  # type: ignore[attr-defined]
        profile_mark(profile, "storage:store_payment_evidence", stage_started)
        stage_started = time.perf_counter()
        file = self._repository.create_payment_evidence_file(  # type: ignore[attr-defined]
            file_id=file_id,
            owner_user_id=user.id,
            payment_report_id=payment_report_id,
            storage_path=stored.storage_path,
            mime_type=mime_type,
            size_bytes=stored.size_bytes,
            content_sha256=content_sha256,
            order_id=order_id,
        )
        profile_mark(profile, "repo:create_payment_evidence_file", stage_started)
        return file

    def _audit_payment_evidence_upload(self, *, user: UserRecord, order_id: str, file, payment_report_id: str, request_id: str, profile: list[dict[str, Any]] | None) -> None:  # type: ignore[no-untyped-def]
        stage_started = time.perf_counter()
        self._audit.write(  # type: ignore[attr-defined]
            event_type="payment_evidence_uploaded",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="order",
            resource_id=order_id,
            request_id=request_id,
            metadata_json={"file_id": file.id, "file_type": file.file_type, "mime_type": file.mime_type, "size_bytes": file.size_bytes, "pending_payment_report_id": payment_report_id},
        )
        profile_mark(profile, "audit:payment_evidence_uploaded", stage_started)
