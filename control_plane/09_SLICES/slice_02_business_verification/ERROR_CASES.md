# ERROR_CASES.md

Expected errors:

- BUSINESS_NOT_FOUND
- BUSINESS_ALREADY_EXISTS
- BUSINESS_ALREADY_SUBMITTED
- BUSINESS_STATUS_INVALID
- BUSINESS_VERIFICATION_REQUIRED
- BUSINESS_DOCUMENT_REQUIRED
- BUSINESS_DOCUMENT_INVALID
- BUSINESS_DOCUMENT_NOT_FOUND
- ADMIN_REASON_REQUIRED
- FORBIDDEN
- UNAUTHENTICATED
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- VALIDATION_ERROR
- CONFLICT

Rules:

- Use `06_API_CONTRACTS/ERROR_CONTRACT.md`.
- Do not expose stack traces, SQL, secrets, tokens, storage paths, signed URLs after generation, or private storage keys.
- Permission errors must not leak private resource existence.
- UI must map every expected error to a safe user state.

Mappings:

- `BUSINESS_NOT_FOUND`: return 404 or safe 403 if existence would leak private data.
- `BUSINESS_ALREADY_EXISTS`: return 409 when owner already has an active business profile.
- `BUSINESS_ALREADY_SUBMITTED`: return 409 when a pending submission already exists.
- `BUSINESS_STATUS_INVALID`: return 409 when transition is not allowed.
- `BUSINESS_DOCUMENT_REQUIRED`: return 422 when required verification document is missing.
- `BUSINESS_DOCUMENT_INVALID`: return 422 for invalid type, mime or size.
- `BUSINESS_DOCUMENT_NOT_FOUND`: return 404/403 safe error.
- `ADMIN_REASON_REQUIRED`: return 400 when approve, reject or document full view reason is missing.
