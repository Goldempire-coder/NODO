# ACCESS_CONTROL

Estado: OFFICIAL
Ultima actualizacion: 2026-07-11

## Principios

- Backend es autoridad.
- Frontend nunca decide permisos criticos.
- Mutaciones admin requieren rol, reason, audit e idempotency.
- Staff interno no equivale a admin total.
- `support` delegado requiere staff profile activo y permisos activos para operar tickets.

## Controles reales

- Usuarios: `users.role`, `users.status`.
- Negocios: `businesses.verification_status`.
- Acceso negocio: `business_access_links`.
- Staff: `staff_profiles`, `staff_permissions`, `staff_invites`.
- Admin Web: `/api/v1/users/me` con `X-NODO-Surface: admin_web`.
- Business App: `/api/v1/surface/session` con `X-NODO-Surface: business_mini_app`.

## Acciones operativas sensibles

- Suspender/bloquear usuario.
- Suspender/reactivar/revocar/bloquear business access link.
- Ajustar creditos.
- Revisar/rechazar compra de creditos.
- Resolver disputa formal.
- Gestionar staff.
- Ver documentos privados con signed URL.

## Prohibiciones

- No entregar `super_admin` a empleados operativos.
- No activar staff sin rol base compatible.
- No usar Telegram ID como autorizacion final.
- No copiar signed URLs a canales externos.
- No exportar datos sensibles sin contrato.
