# SECURITY_CONTRACT.md

## Auth/RBAC

- JWT requerido.
- Backend RBAC obligatorio.
- `admin` y `super_admin` pueden leer y mutar segun matriz.
- `support` puede leer enmascarado/read-only.
- Ningun permiso depende solo del frontend.

## Mutaciones criticas

Requieren:
- reason no vacio;
- `Idempotency-Key`;
- audit log;
- rate limit admin critical action;
- confirmacion visual en UI;
- proteccion de ultimo `super_admin active`.

## Datos sensibles

Prohibido exponer:
- tokens;
- refresh hashes;
- session internals;
- Authorization headers;
- `storage_path`;
- `account_value`;
- datos bancarios completos;
- secretos;
- signed URLs persistidas.

Telegram ID completo:
- permitido solo a `admin`/`super_admin` en endpoints de usuarios;
- `support` solo masked.

Phone:
- masked por defecto en listas;
- detalle completo solo si el contrato de endpoint y RBAC lo permiten para tarea admin.

## Surface impact

- Usuario `restricted`, `blocked` o `dormant` no entra a Mini App Negocio.
- Link `suspended`, `revoked` o `blocked` bloquea Mini App Negocio aunque el usuario este activo.
- Business suspend/block sigue siendo control separado.
