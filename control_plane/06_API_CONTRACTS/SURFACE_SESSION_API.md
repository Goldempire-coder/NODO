# SURFACE_SESSION_API.md

## Objetivo

Contrato para resolver la superficie activa sin cambiar auth base. El frontend puede pedir una superficie, pero el backend decide si el usuario puede entrar y que capacidades recibe.

## Endpoints

### GET /api/v1/surface/session

Headers:
- `Authorization: Bearer <access_token>`
- `X-NODO-Surface: client_mini_app | business_mini_app | admin_web`

Response 200:
```json
{
  "data": {
    "allowed": true,
    "surface": "business_mini_app",
    "actor_role": "business_owner",
    "access_state": "allowed",
    "capabilities": ["business.dashboard", "ads.create"],
    "user": {
      "id": "uuid",
      "role": "business_owner",
      "status": "active"
    },
    "business": {
      "id": "uuid",
      "verification_status": "approved",
      "access_link_status": "active"
    },
    "admin_readonly": false
  }
}
```

Rules:
- Backend calcula capabilities.
- Frontend no puede elevar permisos por surface header.
- Si actor no puede entrar en superficie: error seguro segun `ERROR_CONTRACT.md`.
- Para `business_mini_app`, debe existir negocio aprobado y `business_access_links.status = active`.
- Para `business_mini_app`, el Telegram initData validado debe pertenecer al `users.telegram_id` vinculado por `business_access_links.telegram_id_snapshot`.
- Para `admin_web`, actor debe ser `admin`, `super_admin` o `support`.
- Para `client_mini_app`, actor debe estar autenticado y no bloqueado.

Business Mini App access matrix:

- no linked business: deny `SURFACE_ACCESS_DENIED`, `access_state = no_business_link`.
- business `pending`/`rejected`: deny `BUSINESS_NOT_APPROVED`, `access_state = business_not_approved`.
- business `suspended`: deny mutations; response may return `allowed = false`, `access_state = business_suspended`, history/read-only capabilities only if explicitly contracted.
- business `blocked`: deny all business operations, `access_state = business_blocked`.
- user `restricted`: deny `business_mini_app` until owner defines a restricted-business-access exception; `access_state = user_not_active`.
- user `blocked`/`dormant`: deny `USER_BLOCKED` or `USER_NOT_ACTIVE`.
- link `suspended`: deny operational access, `access_state = link_suspended`.
- link `revoked`: deny access, `access_state = link_revoked`.
- link `blocked`: deny access, `access_state = link_blocked`.

Forbidden:

- Mini App Negocio must not use `/api/v1/businesses/me` as the access gate.
- Query params such as `?surface=business` are only routing hints; they are not authorization.
- Bot messages/buttons do not grant access.

Audit:
- `surface_access_denied` solo en denegaciones o intentos sospechosos.
- `business_access_linked`, `business_access_unlinked`, `business_access_suspended`, `business_access_reactivated` y `business_access_blocked` pertenecen a operaciones admin sobre links.
