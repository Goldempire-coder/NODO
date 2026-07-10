# DATA_CONTRACT.md

## Tabla canonica

`business_access_links`

Columnas:
- id
- business_id
- user_id
- telegram_id_snapshot
- role_in_business
- status
- linked_by_admin_id
- linked_at
- suspended_at
- blocked_at
- revoked_at
- reason
- created_at
- updated_at

Reglas:
- `status`: `active`, `suspended`, `revoked`, `blocked`.
- `role_in_business`: `owner`, `operator`; `operator` reservado futuro.
- Acceso MVP requiere `role_in_business = owner`.
- Link suspendido/revocado/bloqueado no borra user ni negocio.
- Business suspendido/bloqueado no implica automaticamente user bloqueado.
