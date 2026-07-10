# slice_06_business_order_ops Evidence

Estado final: READY_FOR_OWNER_REVIEW

## Implementacion verificada

- Endpoints backend construidos:
  - GET /api/v1/business/orders
  - GET /api/v1/business/orders/{id}
  - POST /api/v1/business/orders/{id}/confirm-payment
  - POST /api/v1/business/orders/{id}/reject-payment-report
  - POST /api/v1/business/orders/{id}/mark-delivered
- Pantallas frontend construidas:
  - B-11_INCOMING_ORDERS
  - B-12_BUSINESS_ORDER_DETAIL
- Migracion creada:
  - database/migrations/0007_slice_06_business_order_ops.up.sql
  - database/migrations/0007_slice_06_business_order_ops.down.sql

## Evidencia de reglas criticas

- Confirm-payment cambia order a `payment_confirmed`, payment report a `accepted`, consume creditos bloqueados exactamente una vez y archiva anuncio (`ad.status = archived`).
- Reject-payment-report cambia order a `payment_rejected`, payment report a `rejected`, no consume creditos y mantiene anuncio `in_order`.
- Mark-delivered cambia order a `delivered`, setea timers de auto-complete futuro y no completa la orden.
- Business owner solo lista/detalla/opera ordenes de su propio `business_id`.
- No se construyeron endpoints de chat/disputas.
- Respuestas y UI no exponen `storage_path`, `account_value`, instrucciones completas ni secretos.

## Comandos ejecutados

- `corepack pnpm --filter @nodo/web build` -> OK
- `python scripts\run_slice_00_tests.py` -> 6 passed
- `python scripts\run_slice_01_tests.py` -> 6 passed
- `python scripts\run_slice_02_tests.py` -> OK, 9 passed, 1 warning Starlette/httpx
- `python scripts\run_slice_03_tests.py` -> OK, 11 passed, 1 warning Starlette/httpx
- `python scripts\run_slice_04_tests.py` -> OK, 9 passed, 1 warning Starlette/httpx
- `python scripts\run_slice_05_tests.py` -> OK, 7 passed, 1 warning Starlette/httpx
- `python scripts\run_slice_06_tests.py` -> OK, 6 passed, 1 warning Starlette/httpx
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` -> 57 passed, 1 warning
- `python -m ruff check apps\api scripts` -> OK
- `python -m compileall apps scripts` -> OK
- Frontend source/build scan for secrets/private data -> OK, no hits

## Riesgos residuales heredados

- Migraciones reales contra PostgreSQL/Supabase pendientes hasta credenciales/servicio real.
- Redis real pendiente.
- Storage privado real pendiente.
- Smoke manual Telegram real pendiente.
- Warning Starlette/httpx aceptado temporalmente.
- Compra/acreditacion real de creditos queda para slice_08.
- Runtime Postgres debe seguir usando Jsonb/adaptadores seguros para columnas jsonb.
- IDs de entrada hacia columnas UUID deben seguir validandose antes de tocar Postgres.

## Scope no construido

- No slice_07.
- No chat.
- No disputas.
- No confirmacion de recibido por remitente.
- No auto-complete.
- No jobs masivos.
- No admin override.
- No compra/acreditacion real de creditos.
- No B-13, R-09 ni R-10.

