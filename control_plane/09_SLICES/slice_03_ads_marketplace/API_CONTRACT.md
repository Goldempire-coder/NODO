# API_CONTRACT.md

Endpoints authorized for this slice:

- GET /api/v1/ads/search
- GET /api/v1/ads/{id}
- POST /api/v1/business/ads
- GET /api/v1/business/ads
- GET /api/v1/business/ads/archived
- PUT /api/v1/business/ads/{id}
- POST /api/v1/business/ads/{id}/pause
- POST /api/v1/business/ads/{id}/archive

Canonical detailed contract:

- `control_plane/06_API_CONTRACTS/ADS_API.md`

API rules:

- Use `/api/v1` prefix.
- Mutating endpoints require auth, RBAC, ownership, state validation, rate limit, idempotency and audit when sensitive.
- Read endpoints require auth and rate limit.
- `GET /api/v1/business/ads` powers B-09 active/paused/in_order list.
- `GET /api/v1/business/ads/archived` powers B-10 archived/expired history.
- Cursor pagination is required for search and owner lists.
- Responses must follow `06_API_CONTRACTS/ERROR_CONTRACT.md`.
- Frontend cannot bypass backend permissions.
- No endpoint in this slice creates orders, payment reports, chat, disputes, credit purchases or Stripe flows.
