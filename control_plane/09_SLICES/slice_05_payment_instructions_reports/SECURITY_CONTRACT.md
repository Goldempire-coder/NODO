# SECURITY_CONTRACT.md

Security requirements for `slice_05_payment_instructions_reports`.

## Auth and ownership

- Auth JWT required for all endpoints.
- Actor must be active `remitter`.
- Remitter can access only own order.
- Permission errors must not leak private resource existence.
- Business owner cannot confirm/reject payment in this slice.
- Admin override is not in this slice.

## Sensitive data

- Full payment instructions are returned only by `GET /api/v1/orders/{id}/payment-instructions`.
- General order detail/list must not expose full `account_value`.
- `account_value` must not appear in logs or audit metadata.
- `tx_hash` may be stored internally but UI/list/audit must mask or truncate.
- `storage_path` never appears in API public responses, frontend, logs or audit metadata.
- Do not log tokens, secrets, raw signed URLs or storage keys.

## Evidence storage

- Payment evidence uses `file_assets`.
- `file_assets.resource_type = payment_report`.
- `file_assets.file_type = payment_evidence`.
- Private storage is mandatory.
- Signed URLs are short-lived and not persisted.
- If real private storage is unavailable in runtime normal, return `STORAGE_UNAVAILABLE`.

## Rate limits

Apply backend rate limits to:

- `GET /api/v1/orders/{id}/payment-instructions`
- `POST /api/v1/orders/{id}/payment-evidence`
- `POST /api/v1/orders/{id}/payment-report`

Dimensions should include user, IP, route/action and order where applicable.

## Idempotency

- `payment-report` requires `Idempotency-Key`.
- `payment-evidence` requires `Idempotency-Key`.
- Same key + same payload returns same result.
- Same key + different payload returns `IDEMPOTENCY_PAYLOAD_MISMATCH` or `IDEMPOTENCY_CONFLICT`.

## Audit

Required audit events:

- `payment_instructions_viewed`
- `payment_evidence_uploaded`
- `payment_reported`

Audit metadata must be masked and must not include full payment instructions, full account values, full tx hashes where not needed, storage paths, tokens or secrets.

If any control is missing, stop with `BLOCKED_BY_SECURITY_GAP`.
