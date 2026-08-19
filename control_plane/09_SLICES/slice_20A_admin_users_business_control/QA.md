# QA.md

Tests obligatorios:

- admin lista usuarios con filtros y paginacion.
- support lista usuarios masked/read-only.
- business_owner/remitter no acceden a admin users.
- admin ve detalle seguro sin tokens/session hashes.
- support detalle masked.
- suspend requiere reason.
- suspend requiere `Idempotency-Key`.
- suspend setea `users.status = restricted`.
- reactivate setea `restricted|dormant|blocked -> active`.
- block setea `active|restricted|dormant -> blocked`.
- blocked user no accede a superficies.
- un desbloqueo Admin auditado restaura acceso solo si las demas restricciones de superficie permiten entrada.
- admin no muta admin/super_admin.
- super_admin puede mutar admin segun contrato.
- no se puede bloquear ultimo super_admin active.
- mutation duplicada con misma idempotency key no duplica audit/efecto.
- misma key con payload distinto falla.
- admin lista access links por business y por user.
- support no crea/suspende/reactiva/revoca/bloquea access links.
- suspended/revoked/blocked link bloquea Mini App Negocio.
- audit events completos.
- responses/logs/audit no exponen `storage_path`, `account_value`, tokens, secrets, refresh hashes ni datos bancarios completos.

Validaciones:
- pytest acumulado.
- ruff.
- compileall.
- frontend build si se toca Admin Web.
- scan frontend/source/build para secretos y datos privados.
