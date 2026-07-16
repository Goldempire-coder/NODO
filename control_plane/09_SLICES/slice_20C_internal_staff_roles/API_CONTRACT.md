# API_CONTRACT.md

La API canonica del slice esta en `control_plane/06_API_CONTRACTS/STAFF_API.md`.

Endpoints activos:

- `GET /api/v1/admin/staff`
- `GET /api/v1/admin/staff/{id}`
- `POST /api/v1/admin/staff/invites`
- `POST /api/v1/admin/staff/{id}/activate`
- `POST /api/v1/admin/staff/{id}/suspend`
- `POST /api/v1/admin/staff/{id}/revoke`
- `POST /api/v1/admin/staff/{id}/permissions`
- `GET /api/v1/admin/staff/{id}/activity`

Mutaciones requieren `Authorization`, `X-NODO-Surface: admin_web`, `Idempotency-Key`, `reason`, RBAC backend y audit.
