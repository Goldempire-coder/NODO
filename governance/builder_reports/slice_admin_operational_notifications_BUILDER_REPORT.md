# slice_admin_operational_notifications Builder Report

Estado: READY_FOR_OWNER_REVIEW

## Resumen

Se implemento una bandeja ligera de notificaciones operativas para Admin Web, separada de `notification_jobs`, audit logs y observability.

La nueva bandeja usa tabla propia `admin_notifications`, API admin propia y UI compacta en el topbar. Los productores MVP crean senales seguras para revision operativa sin convertir jobs, audit logs ni payloads privados en una inbox.

## Archivos tocados

- `database/migrations/0032_admin_operational_notifications.up.sql`
- `database/migrations/0032_admin_operational_notifications.down.sql`
- `apps/api/app/main.py`
- `apps/api/app/modules/admin_notifications/*`
- `apps/api/app/modules/business_intake/*`
- `apps/api/app/modules/support/routes.py`
- `apps/api/app/modules/support/service.py`
- `apps/api/app/modules/credits/routes.py`
- `apps/api/app/modules/credits/service.py`
- `apps/api/app/modules/credits/business_purchases.py`
- `apps/api/app/modules/credits/watcher.py`
- `apps/api/app/modules/notifications/telegram_sender.py`
- `apps/api/tests/test_admin_operational_notifications.py`
- `apps/web/src/api/admin.ts`
- `apps/web/src/types/admin.ts`
- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/hooks/admin-web/useAdminNotificationsModel.ts`
- `apps/web/src/screens/admin-web/AdminWebShell.tsx`
- `apps/web/src/app/admin-web.css`
- `evidence/slice_runs/slice_admin_operational_notifications_evidence.md`

## Migracion

Nueva migracion reversible:

- Up: crea `admin_notifications` con estados `unread`, `read`, `dismissed`, `resolved`; prioridades `info`, `attention`, `high`, `critical`; dedupe unico e indices operativos.
- Down: elimina indices y tabla.

## Backend

- Nuevo modulo `admin_notifications` con modelos, redaccion, repositorios in-memory/Postgres, service, serializers y routes.
- API admin:
  - `GET /api/v1/admin/notifications`
  - `GET /api/v1/admin/notifications/unread-count`
  - `POST /api/v1/admin/notifications/{id}/read`
  - `POST /api/v1/admin/notifications/{id}/dismiss`
  - `POST /api/v1/admin/notifications/{id}/resolve`
- `read/dismiss/resolve` requieren admin mutation.
- Si una misma senal operativa vuelve a ocurrir con el mismo `dedupe_key`, la bandeja reabre la notificacion como `unread` y limpia marcas previas de lectura, descarte o resolucion.

## Productores MVP

- `business_intake_submitted`
- `business_document_uploaded`
- `business_support_ticket_created`
- `base_usdc_credit_purchase_under_review`
- `base_usdc_credit_purchase_stuck`
- `base_usdc_credit_purchase_expired` / `failed` / `verification_failed` cuando el estado existente lo expone
- `telegram_notification_failed_permanent`

No se notifica `pending_payment` normal.

El watcher BASE pagina compras `pending_payment` y `expired` para no limitar la alerta al primer lote.

## Frontend

- Admin Web agrega boton compacto de notificaciones con contador unread.
- Panel scrollable muestra prioridad, titulo, resumen seguro y acciones.
- Abrir notificacion navega a intake, soporte, compras de credito o jobs si la ruta interna lo permite.
- Las acciones `Leida`, `Descartar` y `Resolver` solo se muestran a roles con permiso de mutacion admin.
- No se agrego WebSocket ni infraestructura nueva.

## Seguridad y privacidad

La redaccion central elimina o bloquea metadatos sensibles como:

- tokens
- secrets
- `storage_path`
- `account_value`
- `signed_url`
- `tx_hash`
- payloads Telegram completos
- mensajes privados completos
- PIN
- wallets completas

El resumen de tickets de soporte de negocio es generico; no copia el asunto libre del negocio a la campana admin.

## Validaciones

- `python -m pytest apps/api/tests/test_admin_operational_notifications.py -q --tb=short`: 7 passed
- `python -m pytest apps/api/tests/test_jobs_notifications.py apps/api/tests/test_support_ticket_center.py apps/api/tests/test_credits_referrals.py -q --tb=short`: 48 passed
- `python -m pytest apps/api/tests -q`: 407 passed
- `python -m ruff check apps/api scripts`: passed
- `python -m compileall apps/api apps/web/src scripts`: passed
- `pnpm --filter @nodo/web build`: blocked first because `node` was not in PATH; passed with Cursor helper Node prepended to PATH.
- Secret scan focalizado en archivos del slice: sin secretos reales; solo aparecen claves de redaccion esperadas en `admin_notifications/redaction.py`.

## Riesgos pendientes

- No hay UI admin dedicada para historico/resueltos; el slice implementa bandeja compacta MVP.
- No hay WebSocket/push; contador se refresca por polling existente.
- La senal `stuck` de compras BASE no cambia lifecycle; solo alerta a admin.
- Si el owner quiere ownership granular staff para resolver notificaciones, requiere slice separado.

## Confirmaciones

- No deploy.
- No produccion.
- No infraestructura nueva.
- No secretos agregados.
- No uso de `notification_jobs` como inbox.
- No READY_FOR_REAL_USE.
