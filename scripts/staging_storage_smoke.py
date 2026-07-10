from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx

from local_hardening_common import add_api_path, write_json
from staging_guardrails import guardrail_payload, redact_text, require_staging_guardrails

add_api_path()
from app.shared.storage.supabase import SupabasePrivateStorage  # noqa: E402


def _delete_object(*, supabase_url: str, service_role_key: str, bucket: str, object_path: str) -> None:
    url = f"{supabase_url.rstrip('/')}/storage/v1/object/{quote(bucket, safe='')}/{quote(object_path, safe='/')}"
    headers = {"Authorization": f"Bearer {service_role_key}", "apikey": service_role_key}
    response = httpx.delete(url, headers=headers, timeout=10.0)
    if response.status_code not in {200, 204, 404}:
        raise RuntimeError(f"STORAGE_CLEANUP_FAILED:{response.status_code}")


def run_storage_smoke(env: dict[str, str], *, run_id: str) -> dict:
    supabase_url = env.get("SUPABASE_URL", "").rstrip("/")
    service_role_key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    bucket = env.get("SUPABASE_STORAGE_BUCKET_BUSINESS_INTAKE", "business-intake")
    storage = SupabasePrivateStorage(
        supabase_url=supabase_url,
        service_role_key=service_role_key,
        business_verification_bucket=env.get("SUPABASE_STORAGE_BUCKET_BUSINESS_VERIFICATION", "business-verification"),
        payment_evidence_bucket=env.get("SUPABASE_STORAGE_BUCKET_PAYMENT_EVIDENCE", "payment-evidence"),
        credit_purchase_proofs_bucket=env.get("SUPABASE_STORAGE_BUCKET_CREDIT_PURCHASE_PROOFS", "credit-purchase-proofs"),
        message_attachments_bucket=env.get("SUPABASE_STORAGE_BUCKET_MESSAGE_ATTACHMENTS", "message-attachments"),
        business_intake_bucket=bucket,
    )
    intake_id = f"staging-smoke-{run_id}"
    file_id = str(uuid.uuid4())
    content = f"NODO staging storage smoke {run_id}".encode("utf-8")
    checksum = hashlib.sha256(content).hexdigest()
    stored = storage.store_business_intake_document(
        intake_id=intake_id,
        file_id=file_id,
        file_name="smoke.pdf",
        content=content,
    )
    signed_url = storage.signed_view_url(storage_path=stored.storage_path, expires_in=60)
    download = httpx.get(signed_url, timeout=10.0)
    if download.status_code >= 400:
        raise RuntimeError(f"STORAGE_SIGNED_DOWNLOAD_FAILED:{download.status_code}")
    downloaded_checksum = hashlib.sha256(download.content).hexdigest()
    bucket_name, object_path = storage._parse_storage_path(stored.storage_path)  # noqa: SLF001
    _delete_object(
        supabase_url=supabase_url,
        service_role_key=service_role_key,
        bucket=bucket_name,
        object_path=object_path,
    )
    return {
        "bucket": bucket_name,
        "object_deleted": True,
        "size_bytes": len(content),
        "checksum_sha256": checksum,
        "downloaded_checksum_sha256": downloaded_checksum,
        "checksum_match": checksum == downloaded_checksum,
        "signed_url_created": True,
        "storage_path_exposed": False,
        "signed_url_persisted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()
    guardrails = require_staging_guardrails(
        env_file=Path(args.env_file),
        mutating=True,
        confirm_staging=args.confirm_staging,
        run_id=args.run_id,
    )
    payload = {
        "slice": "slice_17A_staging_validation_tooling",
        "phase": "staging_storage_smoke",
        "guardrails": guardrail_payload(guardrails),
        "result": {},
        "failures": [],
        "exit_code": 0,
    }
    try:
        payload["result"] = run_storage_smoke(guardrails.env, run_id=args.run_id)
        if not payload["result"]["checksum_match"]:
            payload["failures"].append("checksum_mismatch")
    except Exception as exc:
        payload["failures"].append(f"{type(exc).__name__}:{redact_text(str(exc))}")
    payload["exit_code"] = 1 if payload["failures"] else 0
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
