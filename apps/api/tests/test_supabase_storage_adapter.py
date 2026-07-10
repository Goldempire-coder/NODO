from __future__ import annotations

import hashlib
import json
import os

import httpx

from app.core.config import EnvValidationError, load_settings, redact_env_value
from app.core.errors import ApiError
from app.shared.storage.private import SupabasePrivateStorage


def _supabase_storage() -> tuple[SupabasePrivateStorage, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "/storage/v1/object/sign/" in request.url.path:
            return httpx.Response(
                200,
                json={"signedURL": "/object/sign/business-verification/biz/file.pdf?token=mocked"},
            )
        return httpx.Response(200, json={"Key": "ok"})

    return (
        SupabasePrivateStorage(
            supabase_url="https://example-project.supabase.co",
            service_role_key="test-service-role-key",
            business_verification_bucket="business-verification",
            payment_evidence_bucket="payment-evidence",
            credit_purchase_proofs_bucket="credit-purchase-proofs",
            message_attachments_bucket="message-attachments",
            transport=httpx.MockTransport(handler),
        ),
        requests,
    )


def test_supabase_storage_uploads_business_verification_to_private_bucket() -> None:
    storage, requests = _supabase_storage()

    stored = storage.store(
        business_id="biz",
        file_id="file",
        file_name="verification.pdf",
        content=b"private-document",
    )

    assert stored.storage_path == "supabase://business-verification/biz/file.pdf"
    assert stored.size_bytes == len(b"private-document")
    assert stored.checksum_sha256 == hashlib.sha256(b"private-document").hexdigest()
    request = requests[-1]
    assert request.url.path == "/storage/v1/object/business-verification/biz/file.pdf"
    assert request.headers["authorization"] == "Bearer test-service-role-key"
    assert request.headers["apikey"] == "test-service-role-key"
    assert request.headers["x-upsert"] == "false"
    assert request.headers["content-type"] == "application/pdf"


def test_supabase_storage_uses_canonical_buckets_for_all_private_file_families() -> None:
    storage, _requests = _supabase_storage()

    payment = storage.store_payment_evidence(
        order_id="order",
        payment_report_id="report",
        file_id="proof",
        file_name="proof.png",
        content=b"proof",
    )
    message = storage.store_message_attachment(
        order_id="order",
        attachment_id="attachment",
        file_id="message-file",
        file_name="message.webp",
        content=b"message",
    )
    credit = storage.store_credit_purchase_proof(
        business_id="biz",
        purchase_id="purchase",
        file_id="receipt",
        file_name="receipt.jpg",
        content=b"receipt",
    )

    assert payment.storage_path == "supabase://payment-evidence/order/report/proof.png"
    assert message.storage_path == "supabase://message-attachments/order/attachment/message-file.webp"
    assert credit.storage_path == "supabase://credit-purchase-proofs/biz/purchase/receipt.jpg"


def test_supabase_signed_url_is_short_lived_and_does_not_return_raw_storage_path() -> None:
    storage, requests = _supabase_storage()

    signed_url = storage.signed_view_url(
        storage_path="supabase://business-verification/biz/file.pdf",
        expires_in=999,
    )

    request = requests[-1]
    assert request.url.path == "/storage/v1/object/sign/business-verification/biz/file.pdf"
    assert json.loads(request.read()) == {"expiresIn": 300}
    assert signed_url == "https://example-project.supabase.co/storage/v1/object/sign/business-verification/biz/file.pdf?token=mocked"
    assert "supabase://business-verification/biz/file.pdf" not in signed_url


def test_supabase_storage_returns_safe_errors_without_secret_values() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream leaked detail should not be returned")

    storage = SupabasePrivateStorage(
        supabase_url="https://example-project.supabase.co",
        service_role_key="test-service-role-key",
        business_verification_bucket="business-verification",
        payment_evidence_bucket="payment-evidence",
        credit_purchase_proofs_bucket="credit-purchase-proofs",
        message_attachments_bucket="message-attachments",
        transport=httpx.MockTransport(handler),
    )

    try:
        storage.store(business_id="biz", file_id="file", file_name="document.pdf", content=b"x")
    except ApiError as exc:
        assert exc.code == "STORAGE_UNAVAILABLE"
        assert "test-service-role-key" not in exc.message
        assert "upstream leaked detail" not in exc.message
    else:
        raise AssertionError("Supabase 5xx must return a safe storage error")


def test_supabase_storage_mode_requires_backend_only_env_keys() -> None:
    base_env = {
        "APP_ENV": "staging",
        "APP_VERSION": "slice-13",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:5432/nodo",
        "REDIS_URL": "redis://127.0.0.1:6379/0",
        "PRIVATE_STORAGE_MODE": "supabase",
    }

    try:
        load_settings(base_env)
    except EnvValidationError as exc:
        assert set(exc.missing_keys) == {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}
    else:
        raise AssertionError("Supabase storage mode must require Supabase URL and service role key")

    settings = load_settings(
        {
            **base_env,
            "SUPABASE_URL": "https://example-project.supabase.co/",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        }
    )
    assert settings.private_storage_mode == "supabase"
    assert settings.supabase_url == "https://example-project.supabase.co"
    assert settings.supabase_storage_bucket_business_verification == "business-verification"
    assert settings.supabase_storage_bucket_payment_evidence == "payment-evidence"
    assert settings.supabase_storage_bucket_credit_purchase_proofs == "credit-purchase-proofs"
    assert settings.supabase_storage_bucket_message_attachments == "message-attachments"
    assert redact_env_value("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key") == "[REDACTED]"


def test_main_app_activates_supabase_adapter_for_non_test_runtime() -> None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("APP_VERSION", "slice-13")
    os.environ.setdefault("DATABASE_URL", "postgresql://user:password@127.0.0.1:5432/nodo")
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
    from app.main import build_private_storage

    settings = load_settings(
        {
            "APP_ENV": "staging",
            "APP_VERSION": "slice-13",
            "DATABASE_URL": "postgresql://user:password@127.0.0.1:5432/nodo",
            "REDIS_URL": "redis://127.0.0.1:6379/0",
            "PRIVATE_STORAGE_MODE": "supabase",
            "SUPABASE_URL": "https://example-project.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        }
    )

    assert isinstance(build_private_storage(settings), SupabasePrivateStorage)
