# BUILDER_REPORT - slice_06_business_order_ops

Estado final: READY_FOR_OWNER_REVIEW

## Resumen exacto

Se construyo `slice_06_business_order_ops` para que un `business_owner` activo con negocio aprobado pueda listar ordenes propias, ver detalle operativo, confirmar pago recibido, rechazar reporte de pago y marcar pago movil enviado. No se declaro `READY_FOR_REAL_USE`.

## Archivos modificados/creados

- `apps/api/app/core/errors.py`: errores de confirm/reject/deliver, hold/consume y payment report.
- `apps/api/app/modules/orders/models.py`: estado persistente `payment_rejected`.
- `apps/api/app/modules/orders/policy.py`: policy de `business_owner` activo.
- `apps/api/app/modules/orders/state_machine.py`: guards de confirmacion, rechazo y entrega.
- `apps/api/app/modules/orders/repository.py`: list/detail por negocio, payment report latest/update, evidencia y timeline.
- `apps/api/app/modules/ads/repository.py`: consumo de creditos bloqueados y archivado de anuncio.
- `apps/api/app/modules/orders/service.py`: logica de negocio slice 06, RBAC/ownership, idempotencia, auditoria y respuestas masked.
- `apps/api/app/modules/orders/routes.py`: endpoints canonicos `/api/v1/business/orders...`.
- `apps/web/src/app/page.tsx`: vistas B-11/B-12, actions y copy obligatorio.
- `apps/api/tests/test_business_order_ops.py`: tests focales slice 06.
- `scripts/run_slice_06_tests.py`: runner/evidencia del slice.
- `database/migrations/0007_slice_06_business_order_ops.up.sql`: constraints/indices slice 06.
- `database/migrations/0007_slice_06_business_order_ops.down.sql`: rollback.
- `evidence/slice_runs/slice_06_business_order_ops_evidence.md`: evidencia humana.
- `evidence/slice_runs/slice_06_business_order_ops_test_results.json`: evidencia JSON generada por runner.
- `governance/builder_reports/slice_06_business_order_ops_BUILDER_REPORT.md`: este reporte.

## Lineas relevantes

- Routes: `apps/api/app/modules/orders/routes.py:55`, `:66`, `:71`, `:85`, `:99`.
- Servicio: `apps/api/app/modules/orders/service.py:121`, `:553`, `:566`, `:595`, `:651`, `:691`, `:740`.
- Repositorio ordenes: `apps/api/app/modules/orders/repository.py:158`, `:169`, `:210`, `:222`, `:419`, `:435`, `:491`, `:507`, `:521`.
- Repositorio ads/creditos: `apps/api/app/modules/ads/repository.py:216`, `:568`.
- Estado/errores: `apps/api/app/modules/orders/models.py:20`, `apps/api/app/core/errors.py:51`, `:57`.
- Migracion: `database/migrations/0007_slice_06_business_order_ops.up.sql:7`, `:22`, `:38`.
- UI: `apps/web/src/app/page.tsx:207`, `:267`, `:815`, `:834`, `:850`, `:1462`, `:1491`.
- Tests: `apps/api/tests/test_business_order_ops.py:192`, `:214`, `:266`, `:291`, `:321`, `:362`.

## Endpoints construidos

- `GET /api/v1/business/orders`
- `GET /api/v1/business/orders/{id}`
- `POST /api/v1/business/orders/{id}/confirm-payment`
- `POST /api/v1/business/orders/{id}/reject-payment-report`
- `POST /api/v1/business/orders/{id}/mark-delivered`

## Pantallas construidas

- `B-11_INCOMING_ORDERS`
- `B-12_BUSINESS_ORDER_DETAIL`

## Contratos cumplidos

- Auth JWT requerida.
- Actor `business_owner` activo.
- Negocio aprobado requerido.
- Ownership estricto por `business_id`; orden ajena devuelve error seguro.
- Cursor pagination para lista.
- Idempotency-Key obligatorio en mutaciones.
- Confirm-payment:
  - `orders.status = payment_confirmed`
  - `payment_reports.status = accepted`
  - `payment_confirmed_at`, `delivery_warning_at`, `delivery_deadline_at`
  - ledger `consume`
  - `ad.status = archived`
  - audit `payment_confirmed`, `credits_consumed`, `ad_archived`
- Reject-payment-report:
  - reason obligatorio
  - `orders.status = payment_rejected`
  - `payment_reports.status = rejected`
  - no consume creditos
  - `ad.status = in_order`
  - audit `payment_report_rejected`
- Mark-delivered:
  - `orders.status = delivered`
  - `delivered_at`, `auto_complete_warning_12h_at`, `auto_complete_warning_23h_at`, `auto_complete_at`
  - audit `order_delivered`
- No se exponen `storage_path`, `account_value`, instrucciones completas, tokens ni secretos.

## Migraciones

Creada migracion reversible `0007_slice_06_business_order_ops` para:

- Agregar `payment_rejected` al check de `orders.status`.
- Agregar `payment_rejected` a checks de `order_state_events`.
- Agregar indices:
  - `payment_reports_order_status_created_idx`
  - `credits_ledger_reference_type_id_type_idx`
  - `credits_ledger_related_order_type_idx`

No se ejecutaron migraciones contra PostgreSQL/Supabase real por falta de servicio/credenciales; riesgo residual heredado y aceptado temporalmente.

## Tests ejecutados

- `corepack pnpm --filter @nodo/web build` -> OK.
- `python scripts\run_slice_00_tests.py` -> 6 passed.
- `python scripts\run_slice_01_tests.py` -> 6 passed.
- `python scripts\run_slice_02_tests.py` -> 9 passed, 1 warning Starlette/httpx.
- `python scripts\run_slice_03_tests.py` -> 11 passed, 1 warning Starlette/httpx.
- `python scripts\run_slice_04_tests.py` -> 9 passed, 1 warning Starlette/httpx.
- `python scripts\run_slice_05_tests.py` -> 7 passed, 1 warning Starlette/httpx.
- `python scripts\run_slice_06_tests.py` -> 6 passed, 1 warning Starlette/httpx.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` -> 57 passed, 1 warning.
- `python -m ruff check apps\api scripts` -> OK.
- `python -m compileall apps scripts` -> OK.
- Escaneo frontend source/build -> OK, no hits.

## Tests no ejecutados

- Migraciones reales contra PostgreSQL/Supabase: no hay credenciales/servicio real disponible.
- Redis real: no hay servicio real disponible.
- Storage privado real: no hay storage real configurado.
- Smoke manual Telegram real: pendiente por entorno real.

## Evidencia creada

- `evidence/slice_runs/slice_06_business_order_ops_test_results.json`
- `evidence/slice_runs/slice_06_business_order_ops_evidence.md`

## Riesgos residuales

- Riesgos heredados aceptados temporalmente siguen vigentes: PostgreSQL/Supabase real, Redis real, storage privado real, smoke Telegram real y warning Starlette/httpx.
- La operacion de confirm-payment usa proteccion de idempotencia y ledger consume; en Postgres queda encapsulada en `confirm_business_payment_with_credit_consumption` para actualizar orden, reporte, wallet, ledger y anuncio dentro de una transaccion. La ejecucion real contra Postgres sigue pendiente hasta credenciales/servicio real.

## Scope NO construido

- No slice_07.
- No chat.
- No disputas.
- No confirmacion del remitente.
- No auto-complete.
- No jobs masivos.
- No admin override.
- No compra/acreditacion real de creditos.
- No B-13, R-09 ni R-10.

Estado final: READY_FOR_OWNER_REVIEW
