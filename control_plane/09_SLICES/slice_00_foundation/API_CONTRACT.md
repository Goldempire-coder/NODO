# API_CONTRACT.md

Endpoints authorized for this slice:

- GET /health
- GET /ready
- GET /version

API rules:

- Use /api/v1 prefix unless project router defines equivalent grouping.
- Mutating endpoints require auth, RBAC, validation and audit when sensitive.
- Idempotency-Key is required for retryable create/confirm/approve flows.
- Responses must follow 06_API_CONTRACTS/ERROR_CONTRACT.md.
- Frontend cannot bypass backend permissions.