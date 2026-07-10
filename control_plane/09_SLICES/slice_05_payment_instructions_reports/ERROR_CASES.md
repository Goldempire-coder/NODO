# ERROR_CASES.md

Expected errors:

- UNAUTHENTICATED
- FORBIDDEN
- VALIDATION_ERROR
- RATE_LIMITED
- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- ORDER_EXPIRED
- PAYMENT_REPORT_NOT_ALLOWED
- PAYMENT_EVIDENCE_REQUIRED
- PAYMENT_REPORT_ALREADY_SUBMITTED
- INVALID_PAYMENT_METHOD
- INVALID_PAYMENT_EVIDENCE
- STORAGE_UNAVAILABLE
- STORAGE_UPLOAD_FAILED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- IDEMPOTENCY_PAYLOAD_MISMATCH

Rules:

- Use `06_API_CONTRACTS/ERROR_CONTRACT.md`.
- Do not expose stack traces, SQL, secrets, tokens, full account values, full payment instructions, raw tx hashes in broad contexts, storage paths or private storage keys.
- Permission errors must not leak private resource existence.
- UI must map every expected error to a safe user state.
