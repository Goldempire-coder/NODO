# SECURITY_CONTRACT.md

## Auth/RBAC

- Admin Web requiere sesion autenticada.
- `super_admin` administra staff y permisos.
- `admin` puede leer staff si RBAC lo permite.
- `support` y staff delegado no administran staff.
- Backend es autoridad; frontend no concede permisos.

## Prohibiciones

Staff delegado no puede:

- bloquear/suspender usuarios.
- cambiar roles.
- mutar `business_access_links`.
- aprobar/rechazar negocios.
- aprobar/rechazar pagos de creditos.
- hacer ajustes manuales de creditos.
- resolver disputas.
- mutar ordenes, anuncios o creditos.

## Datos sensibles

- Masking por defecto.
- Adjuntos solo con permiso, reason, signed URL corta y audit.
- No exponer `storage_path`, `account_value`, tokens, secretos ni signed URLs persistidas.

## Mutaciones

- Reason obligatorio.
- `Idempotency-Key` obligatorio.
- Audit obligatorio.
- Rate limit obligatorio.
- No hard delete.
