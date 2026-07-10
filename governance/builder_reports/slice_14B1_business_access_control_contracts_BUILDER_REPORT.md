# slice_14B1_business_access_control_contracts BUILDER_REPORT

## Estado final

READY_FOR_OWNER_REVIEW

## Resumen exacto

Se implemento el control de acceso gobernado para Mini App Negocio usando `business_access_links` como vinculo canonico usuario/Telegram/negocio y `GET /api/v1/surface/session` como gate canonico de entrada.

La Mini App Negocio ya no usa `/api/v1/businesses/me` como gate inicial. Primero llama `GET /api/v1/surface/session` con `X-NODO-Surface: business_mini_app`; si el backend no permite acceso, renderiza un estado bloqueado/suspendido/sin vinculo sin acciones operativas.

## Archivos principales modificados

- `apps/api/app/auth/dependencies.py`
- `apps/api/app/core/errors.py`
- `apps/api/app/main.py`
- `apps/api/app/routes/surface.py`
- `apps/api/app/modules/businesses/access_control.py`
- `apps/api/app/modules/businesses/models.py`
- `apps/api/app/modules/businesses/repository.py`
- `apps/api/app/modules/businesses/routes.py`
- `apps/api/app/modules/businesses/schemas.py`
- `apps/api/app/modules/businesses/service.py`
- `apps/api/app/modules/ads/service.py`
- `apps/api/app/modules/orders/service.py`
- `apps/api/app/modules/credits/service.py`
- `apps/api/app/modules/chat/service.py`
- `apps/api/app/modules/disputes/service.py`
- `apps/api/tests/test_business_access_control.py`
- `apps/api/tests/test_ads_marketplace.py`
- `apps/api/tests/test_business_order_ops.py`
- `apps/api/tests/test_chat_disputes.py`
- `apps/api/tests/test_order_creation.py`
- `apps/api/tests/test_payment_instructions_reports.py`
- `apps/api/tests/test_credits_referrals.py`
- `apps/api/tests/test_admin_console.py`
- `apps/api/tests/test_jobs_notifications.py`
- `apps/web/src/api/client.ts`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx`
- `database/migrations/0013_slice_14B1_business_access_links.up.sql`
- `database/migrations/0013_slice_14B1_business_access_links.down.sql`

## Migraciones

Creada migracion reversible `0013_slice_14B1_business_access_links` para:

- tabla `business_access_links`
- FK a `businesses`, `users` y admin actor
- `role_in_business` con `owner` y `operator`
- `status` con `active`, `suspended`, `revoked`, `blocked`
- timestamps de link/suspension/bloqueo/revocacion
- `reason` obligatorio para estados no activos
- indices por negocio, usuario, Telegram snapshot y estado
- unique parcial para vinculo activo negocio/usuario
- unique parcial para un owner activo por negocio

## Endpoints construidos

- `GET /api/v1/surface/session`
- `POST /api/v1/admin/businesses/{id}/access-links`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/suspend`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/reactivate`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/revoke`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/block`

## Reglas implementadas

- `business_mini_app` requiere usuario activo, rol `business_owner`, negocio aprobado, link activo y Telegram snapshot coincidente.
- Usuarios bloqueados en `surface/session` devuelven `USER_BLOCKED`.
- Usuarios no activos devuelven `USER_NOT_ACTIVE`.
- Links `suspended`, `revoked` y `blocked` devuelven errores especificos.
- Admin/super_admin pueden crear y mutar links con `Idempotency-Key` y `reason`.
- `support` no puede mutar links.
- Suspender/revocar/bloquear link no borra usuario ni negocio.
- Operaciones sensibles de negocio ahora reutilizan policy comun de acceso activo.
- Endpoints legacy de negocio no fueron eliminados ni convertidos en gate activo de Mini App Negocio.

## Tests ejecutados

- `corepack pnpm --filter @nodo/web build`: PASS.
- `$env:PYTHONPATH='apps/api;C:\Users\carlo\AppData\Roaming\Python\Python314\site-packages'; python -m pytest apps\api\tests\test_business_access_control.py apps\api\tests\test_ads_marketplace.py -q --tb=short`: PASS, `18 passed, 1 warning`.
- `$env:PYTHONPATH='apps/api;C:\Users\carlo\AppData\Roaming\Python\Python314\site-packages'; python -m pytest apps\api\tests -q --tb=short`: PASS, `110 passed, 1 warning`.
- `python -m ruff check apps\api scripts`: PASS.
- `python -m compileall apps scripts`: PASS.

Warning aceptado: `StarletteDeprecationWarning` heredado de `fastapi.testclient`.

## Scans ejecutados

- `surface/session` presente en `useBusinessMiniAppModel.ts`: PASS.
- `/businesses/me` no usado como gate inicial en `useBusinessMiniAppModel.ts`: PASS.
- `business-app` no importa `ClientWorkspace`, `AdminWebWorkspace`, `RemitterScreens`, `VerificationScreens`, `BusinessOperationsScreens` ni `AdminConsoleScreens`: PASS.
- `business-app`, `useBusinessMiniAppModel.ts` y build `apps/web/out` sin `storage_path`, `account_value`, secretos ni claims prohibidos: PASS.
- `create_business` sigue presente solo como codigo legacy/contrato legacy, no como gate de Mini App Negocio: PASS.

## Que NO construi

- No construi Admin Web nuevo.
- No construi Bot Registro Negocios completo.
- No reconstruí Mini App Cliente.
- No cambie reglas de creditos, ordenes, anuncios, disputas ni pagos.
- No elimine endpoints legacy.
- No hice deploy.
- No declare READY_FOR_REAL_USE.

## Riesgos residuales

- La migracion fue creada y validada por pruebas locales/in-memory; queda pendiente aplicacion real contra infraestructura de staging/produccion cuando el owner lo autorice.
- Los endpoints legacy de self-onboarding siguen existiendo por contrato, pero no son el gate de Mini App Negocio.
- `operator` queda reservado por contrato futuro; en esta implementacion el acceso operativo efectivo sigue exigiendo rol `business_owner`.

