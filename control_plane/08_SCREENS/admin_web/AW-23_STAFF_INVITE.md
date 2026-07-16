# AW-23_STAFF_INVITE.md

## Surface

Admin Web Desktop.

## Objetivo

Crear invitacion o activacion staff gobernada para un usuario existente.

## Campos

- target_user_id o target_telegram_id o target_username.
- staff_role.
- permisos iniciales.
- scope por permiso.
- expires_at.
- reason obligatorio.

## Reglas UI

- No mostrar tokens secretos despues de crear invite.
- No permitir seleccionar permisos prohibidos para staff.
- Mostrar resumen antes de confirmar.
- Mostrar warning de que revocar staff no bloquea necesariamente el usuario.
- Backend valida todo; frontend solo ayuda.

## Seguridad

- Solo `super_admin`.
- Idempotency-Key en submit.
- Audit obligatorio.
- No exportar ni copiar datos sensibles.
