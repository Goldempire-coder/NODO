from __future__ import annotations

import hashlib
import mimetypes
from urllib.parse import quote

import httpx

from app.core.errors import ApiError
from app.shared.storage.models import StoredPrivateFile


class SupabasePrivateStorage:
    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        business_verification_bucket: str,
        payment_evidence_bucket: str,
        credit_purchase_proofs_bucket: str,
        message_attachments_bucket: str,
        business_intake_bucket: str = "business-intake",
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._supabase_url = supabase_url.rstrip("/")
        self._service_role_key = service_role_key
        self._business_verification_bucket = business_verification_bucket
        self._payment_evidence_bucket = payment_evidence_bucket
        self._credit_purchase_proofs_bucket = credit_purchase_proofs_bucket
        self._message_attachments_bucket = message_attachments_bucket
        self._business_intake_bucket = business_intake_bucket
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._http_client = httpx.Client(timeout=self._timeout_seconds, transport=self._transport)

    def _safe_suffix(self, file_name: str) -> str:
        suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
        return "".join(character for character in suffix if character.isalnum())[:12] or "bin"

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _object_url(self, bucket: str, object_path: str) -> str:
        return (
            f"{self._supabase_url}/storage/v1/object/"
            f"{quote(bucket, safe='')}/{quote(object_path, safe='/')}"
        )

    def _sign_url(self, bucket: str, object_path: str) -> str:
        return (
            f"{self._supabase_url}/storage/v1/object/sign/"
            f"{quote(bucket, safe='')}/{quote(object_path, safe='/')}"
        )

    def _storage_path(self, bucket: str, object_path: str) -> str:
        return f"supabase://{bucket}/{object_path}"

    def _parse_storage_path(self, storage_path: str) -> tuple[str, str]:
        if not storage_path.startswith("supabase://"):
            raise ApiError("BUSINESS_DOCUMENT_NOT_FOUND", status_code=404)
        bucket_and_path = storage_path.removeprefix("supabase://")
        bucket, separator, object_path = bucket_and_path.partition("/")
        if not bucket or not separator or not object_path or ".." in object_path.split("/"):
            raise ApiError("BUSINESS_DOCUMENT_NOT_FOUND", status_code=404)
        return bucket, object_path

    def _upload(self, *, bucket: str, object_path: str, file_name: str, content: bytes) -> StoredPrivateFile:
        content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        headers = self._headers(content_type)
        headers["x-upsert"] = "false"
        try:
            response = self._http_client.post(self._object_url(bucket, object_path), headers=headers, content=content)
        except httpx.RequestError as exc:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503) from exc

        if response.status_code >= 500:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        if response.status_code >= 400:
            raise ApiError("STORAGE_UPLOAD_FAILED", status_code=502)

        return StoredPrivateFile(
            storage_path=self._storage_path(bucket, object_path),
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
        )

    def store(self, *, business_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._upload(
            bucket=self._business_verification_bucket,
            object_path=f"{business_id}/{file_id}.{suffix}",
            file_name=file_name,
            content=content,
        )

    def store_payment_evidence(self, *, order_id: str, payment_report_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._upload(
            bucket=self._payment_evidence_bucket,
            object_path=f"{order_id}/{payment_report_id}/{file_id}.{suffix}",
            file_name=file_name,
            content=content,
        )

    def store_message_attachment(self, *, order_id: str, attachment_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._upload(
            bucket=self._message_attachments_bucket,
            object_path=f"{order_id}/{attachment_id}/{file_id}.{suffix}",
            file_name=file_name,
            content=content,
        )

    def store_credit_purchase_proof(self, *, business_id: str, purchase_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._upload(
            bucket=self._credit_purchase_proofs_bucket,
            object_path=f"{business_id}/{purchase_id}/{file_id}.{suffix}",
            file_name=file_name,
            content=content,
        )

    def store_business_intake_document(self, *, intake_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._upload(
            bucket=self._business_intake_bucket,
            object_path=f"{intake_id}/{file_id}.{suffix}",
            file_name=file_name,
            content=content,
        )

    def signed_view_url(self, *, storage_path: str, expires_in: int) -> str:
        bucket, object_path = self._parse_storage_path(storage_path)
        safe_expires_in = min(max(int(expires_in), 1), 300)
        try:
            response = self._http_client.post(
                self._sign_url(bucket, object_path),
                headers=self._headers("application/json"),
                json={"expiresIn": safe_expires_in},
            )
        except httpx.RequestError as exc:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503) from exc

        if response.status_code == 404:
            raise ApiError("BUSINESS_DOCUMENT_NOT_FOUND", status_code=404)
        if response.status_code >= 500:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        if response.status_code >= 400:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)

        signed_url = response.json().get("signedURL") or response.json().get("signedUrl")
        if not isinstance(signed_url, str) or not signed_url:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        if signed_url.startswith("/object/"):
            return f"{self._supabase_url}/storage/v1{signed_url}"
        if signed_url.startswith("/"):
            return f"{self._supabase_url}{signed_url}"
        return signed_url
