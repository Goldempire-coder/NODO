# BUILDER_REPORT - slice_20B_support_ticket_center

## Estado final

READY_FOR_OWNER_REVIEW

## Qué construí

- Centro de soporte backend para tickets, mensajes, adjuntos privados, eventos y cola admin.
- Módulo backend aislado en `apps/api/app/modules/support/`.
- Endpoints cliente/negocio:
  - `POST /api/v1/support/tickets`
  - `GET /api/v1/support/tickets`
  - `GET /api/v1/support/tickets/{ticket_id}`
  - `POST /api/v1/support/tickets/{ticket_id}/messages`
  - `POST /api/v1/support/tickets/{ticket_id}/attachments`
- Endpoints Admin Web:
  - `GET /api/v1/admin/support/tickets`
  - `GET /api/v1/admin/support/tickets/{ticket_id}`
  - `POST /api/v1/admin/support/tickets/{ticket_id}/messages`
  - `POST /api/v1/admin/support/tickets/{ticket_id}/assign`
  - `POST /api/v1/admin/support/tickets/{ticket_id}/escalate`
  - `POST /api/v1/admin/support/tickets/{ticket_id}/resolve`
  - `POST /api/v1/admin/support/tickets/{ticket_id}/close`
  - `POST /api/v1/admin/support/tickets/{ticket_id}/attachments/{file_id}/view-url`
- Migración reversible `0019_slice_20B_support_ticket_center`.
- UI en Mini App Cliente para soporte general/por orden.
- UI en Mini App Negocio para soporte general/orden/anuncio/créditos.
- UI Admin Web desktop para cola, detalle, respuesta, asignación, escalamiento, resolución/cierre y adjuntos privados.
- Tests específicos de soporte y validación acumulada.

## Qué NO construí

- No construí observabilidad/costos de soporte.
- No construí roles internos nuevos fuera de `admin/super_admin/support`.
- No cambié resolución formal de disputas.
- No cambié lifecycle de órdenes, créditos, anuncios, pagos ni disputas.
- No agregué deploy.
- No declaré `READY_FOR_REAL_USE`.

## Archivos principales

- `apps/api/app/modules/support/*`
- `apps/api/app/main.py`
- `apps/api/app/core/errors.py`
- `apps/api/app/shared/storage/memory.py`
- `apps/api/app/shared/storage/local.py`
- `apps/api/app/shared/storage/supabase.py`
- `apps/api/app/shared/storage/unavailable.py`
- `database/migrations/0019_slice_20B_support_ticket_center.up.sql`
- `database/migrations/0019_slice_20B_support_ticket_center.down.sql`
- `apps/api/tests/test_support_ticket_center.py`
- `apps/web/src/api/support.ts`
- `apps/web/src/types/support.ts`
- `apps/web/src/hooks/useSurfaceSupportModel.ts`
- `apps/web/src/hooks/admin-web/useAdminSupportModel.ts`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/screens/client/ClientSupportScreen.tsx`
- `apps/web/src/screens/business-app/BusinessSupportScreen.tsx`
- `apps/web/src/screens/admin-web/AdminSupportScreens.tsx`
- `apps/web/src/app/globals.css`

## Validaciones

- `python -m pytest apps\api\tests\test_support_ticket_center.py -q --tb=short`: `4 passed, 1 warning in 2.84s`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: `187 passed, 1 warning in 42.59s`
- `python -m ruff check apps\api scripts`: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Scans

- Admin Web support scan: sin imports de `ClientWorkspace`, `BusinessMiniAppWorkspace`, `RemitterScreens`, `VerificationScreens`, `BusinessOperationsScreens`, `@telegram-apps/telegram-ui`, `MainButton`, `themeParams` ni bottom nav Telegram en `apps/web/src/screens/admin-web`, `apps/web/src/hooks/admin-web`, `apps/web/src/hooks/useAdminWebModel.ts`.
- Business app scan: sin imports de `ClientWorkspace`, `AdminWeb`, `AdminConsoleScreens`, `VerificationScreens`, `RemitterScreens` ni `BusinessOperationsScreens` en `apps/web/src/screens/business-app`, `apps/web/src/hooks/useBusinessMiniAppModel.ts`, `apps/web/src/hooks/business-mini-app`.
- Frontend source/build scan: sin hits de `SUPABASE_SERVICE_ROLE_KEY`, `BOT_TOKEN`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, `storage_path`, `account_value`, `escrow`, `fondos protegidos`, `pago garantizado`, `garantía de entrega`, `NODO recibió dinero`, private keys, seed phrases ni mnemonics.

## Riesgos residuales

- Los adjuntos de soporte se almacenan como `resource_type=support_ticket`; el contrato permite también `support_message`, pero el MVP implementado evita adjuntos a mensajes para no hacer asociaciones silenciosas.
- Escalar a una disputa existente guarda el vínculo si se envía `existing_dispute_id`, pero no crea ni resuelve disputas. La disputa formal sigue gobernada por su flujo existente.
- No se ejecutó deploy ni smoke contra servicios reales en esta fase.

## Confirmaciones

- No hice deploy.
- No declaré `READY_FOR_REAL_USE`.
- No construí 20C.
- No cambié reglas de órdenes, créditos, anuncios, pagos ni disputas.
- No mezclé soporte con disputa formal.
