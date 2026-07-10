# USERS_API.md

Contrato de usuario autenticado.

## GET /api/v1/users/me

Devuelve perfil propio del usuario autenticado.

Slice 14:
- La respuesta puede incluir capabilities/surfaces calculadas por backend si se mantiene dentro del contrato de `SURFACE_SESSION_API.md`.
- El frontend no puede inferir acceso a Mini App Negocio o Admin Web solo por `role`; debe usar backend capabilities.

Response 200:

```json
{
  "data": {
    "id": "uuid",
    "username": "string|null",
    "first_name": "string|null",
    "last_name": "string|null",
    "role": "remitter|business_owner|admin|super_admin|support",
    "status": "active|restricted|blocked|dormant",
    "trust_level": "string|null",
    "last_seen_at": "timestamp|null"
  },
  "request_id": "req_..."
}
```

Rules:

- Requiere JWT valido.
- Solo devuelve el perfil propio.
- No devuelve `telegram_id`.
- No devuelve secretos ni tokens.
- Usuario `blocked` o suspendido debe recibir error seguro segun auth policy.

## PATCH /api/v1/users/me

Post-MVP salvo aprobacion explicita.

No permite cambiar rol, status, trust_level ni Telegram ID desde usuario.
