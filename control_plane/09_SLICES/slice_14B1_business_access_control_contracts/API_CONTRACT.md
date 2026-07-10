# API_CONTRACT.md

## Gate canonico

`GET /api/v1/surface/session`

Headers:
- `Authorization: Bearer <access_token>`
- `X-NODO-Surface: business_mini_app`

Rules:
- Valida usuario activo.
- Valida rol `business_owner`.
- Valida negocio `approved`.
- Valida `business_access_links.status = active`.
- Valida que Telegram initData pertenezca al usuario vinculado.
- Devuelve capabilities calculadas por backend.

## Admin access link endpoints

Definidos en `ADMIN_API.md`:
- `POST /api/v1/admin/businesses/{id}/access-links`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/suspend`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/reactivate`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/revoke`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/block`

Mutaciones requieren `Authorization`, `Idempotency-Key`, reason, RBAC admin/super_admin y audit.

## Legacy/internal

- `POST /api/v1/businesses`
- `POST /api/v1/businesses/{id}/verification-documents`
- `POST /api/v1/businesses/{id}/submit-verification`

No son flujo activo de Mini App Negocio.
