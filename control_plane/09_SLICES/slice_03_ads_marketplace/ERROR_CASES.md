# ERROR_CASES.md

Expected errors:

- AD_NOT_FOUND
- AD_NOT_AVAILABLE
- AD_STATUS_INVALID
- AD_AMOUNT_RANGE_INVALID
- AD_AMOUNT_TOO_HIGH
- AD_OVERLAP_NOT_ALLOWED
- BUSINESS_NOT_APPROVED
- BUSINESS_NOT_FOUND
- CREDIT_BALANCE_INSUFFICIENT
- CREDIT_WALLET_NOT_FOUND
- INVALID_PAYMENT_METHOD
- INVALID_DELIVERY_METHOD
- PAYMENT_METHOD_NOT_APPROVED
- FORBIDDEN
- UNAUTHENTICATED
- VALIDATION_ERROR
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- STATE_TRANSITION_NOT_ALLOWED

Rules:

- Use `06_API_CONTRACTS/ERROR_CONTRACT.md`.
- Do not expose stack traces, SQL, secrets, tokens or private storage keys.
- Permission errors must not leak private resource existence.
- UI must map every expected error to a safe user state.
- `AD_NOT_FOUND` is for owned resource not found or public detail not found.
- `AD_NOT_AVAILABLE` is for expired, suspended, in_order, archived, or otherwise unavailable public ads.
- `CREDIT_WALLET_NOT_FOUND` may be used only if lazy creation fails safely; normal missing wallet must be initialized with zero balances in slice 03.
