# API_CONTRACT.md

Endpoints authorized for this slice:

- POST /api/v1/auth/telegram
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/users/me

API rules:

- Use /api/v1 prefix unless project router defines equivalent grouping.
- Mutating endpoints require auth, RBAC, validation and audit when sensitive.
- Idempotency-Key is required for retryable create/confirm/approve flows.
- Responses must follow 06_API_CONTRACTS/ERROR_CONTRACT.md.
- Frontend cannot bypass backend permissions.