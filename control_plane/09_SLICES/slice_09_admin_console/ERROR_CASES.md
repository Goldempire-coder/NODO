# ERROR_CASES.md

Expected errors:

- FORBIDDEN
- ADMIN_REASON_REQUIRED
- NOT_FOUND
- DISPUTE_NOT_FOUND
- DISPUTE_STATUS_INVALID
- DISPUTE_RESOLUTION_NOT_ALLOWED
- DISPUTE_RESOLUTION_REASON_REQUIRED
- ORDER_STATUS_INVALID
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- STATE_TRANSITION_NOT_ALLOWED
- RATE_LIMITED
- VALIDATION_ERROR
- SENSITIVE_EXPORT_BLOCKED only if a blocked export endpoint is explicitly implemented

Rules:

- Use 06_API_CONTRACTS/ERROR_CONTRACT.md.
- Do not expose stack traces, SQL, secrets, tokens or private storage keys.
- Permission errors must not leak private resource existence.
- UI must map every expected error to a safe user state.
- Do not use `RESOURCE_NOT_FOUND`; use `NOT_FOUND` or an approved domain error.
