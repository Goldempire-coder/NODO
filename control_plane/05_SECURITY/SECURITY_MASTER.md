# SECURITY_MASTER.md

## Slice 14 - Surface separation, bot and support

- Surface access is enforced by backend RBAC, not frontend hiding.
- Mini App Cliente must not expose business/admin capabilities.
- Mini App Negocio requires approved business and Telegram association.
- Admin Web Desktop requires admin/super_admin/support role and secure session.
- Bot Registro Negocios requires webhook secret/signature validation.
- Business intake documents and support attachments use private storage only.
- Support tickets do not change order state; dispute flow remains formal.
- No logs/audit/API response may include `storage_path`, tokens, secrets, full banking data or private evidence.

Seguridad obligatoria para NODO.

## Reglas madre

- Validar Telegram initData en backend.
- No confiar en frontend.
- JWT corto con refresh controlado.
- RBAC por accion y ownership.
- Storage privado con URLs firmadas.
- Datos sensibles enmascarados.
- Rate limits por usuario/IP/negocio/ruta.
- Audit logs en acciones sensibles.
- Admin actions con confirmacion y nota.
- Secrets fuera del repo y fuera del bundle frontend.

## Superficies de riesgo

- Telegram initData falsificado.
- Webhooks Stripe repetidos o falsos.
- Doble acreditacion de creditos.
- Doble creacion de orden por retry.
- Acceso de negocio a orden ajena.
- Admin panel sin permiso granular.
- Evidencia de pago publica.
- Copy que prometa garantia financiera.

## Controles obligatorios

- Middleware de auth.
- Policy layer por accion.
- State machine para orden, anuncio, negocio, disputa y creditos.
- Idempotency service.
- Audit service append-only.
- Secrets manager/env seguro.
- Upload validator.
- Signed URL service.
- Rate limiter Redis.
- Background jobs con lock.

## Datos sensibles

Enmascarar en UI/admin cuando no sea necesario:

- telefonos
- correos
- cuentas/metodos de pago
- hashes/referencias de comprobantes
- Telegram IDs internos
- storage keys

## Admin

- Admin no puede existir solo por whitelist informal.
- Debe haber roles, permisos, audit logs y sesiones.
- Acciones criticas requieren reason.
- Super admin maneja roles admin.
- Exportaciones sensibles bloqueadas por defecto.

## Criterio de bloqueo

Si una feature toca pagos, creditos, evidencia, admin, verificacion o ordenes sin RBAC y audit log, el builder debe detenerse con `BLOCKED_BY_SECURITY_GAP`.
