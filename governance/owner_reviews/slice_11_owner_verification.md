# OWNER VERIFICATION - slice_11_hardening_deploy

Fecha: 2026-07-04

Estado auditado del builder: READY_FOR_OWNER_REVIEW

Estado owner verification: OWNER_ACCEPTED_LOCAL_HARDENING

## Resultado

La fase local de `slice_11_hardening_deploy` fue auditada contra contratos, scripts, evidencia local y regresion acumulada.

No se declara READY_FOR_REAL_USE.

No se autoriza deploy productivo.

## Hallazgos corregidos

1. El stress inicial era progresivo pero secuencial, no una prueba concurrente real.
   - Se agrego `scripts/concurrency_local.py`.
   - El runner de slice 11 ahora ejecuta una prueba concurrente local con Postgres/Redis.
   - La prueba cubre busqueda concurrente, creacion de ordenes concurrentes y replay concurrente de la misma `Idempotency-Key`.

2. `RedisIdempotencyStore.replay_or_store` hacia `get -> compute -> put` sin lock atomico.
   - Se agrego lock Redis con `SET NX` y espera corta por resultado.
   - Se mantuvo validacion de payload hash y conflicto seguro.
   - `InMemoryIdempotencyStore` ahora serializa `replay_or_store` con lock.

3. `create_order` no usaba el store idempotente global.
   - Se envolvio `create_order` con `idempotency_store.replay_or_store`.
   - La prueba concurrente confirma que 5 requests simultaneos con la misma key devuelven el mismo `order_id` y no crean filas duplicadas.

## Archivos tocados por owner verification

- `apps/api/app/shared/idempotency/store.py`
- `apps/api/app/modules/orders/service.py`
- `scripts/concurrency_local.py`
- `scripts/run_slice_11_tests.py`
- `apps/api/tests/test_hardening_local.py`

## Evidencia nueva

- `evidence/slice_runs/slice_11_local_concurrency.json`

Resultado de concurrencia local:

- total requests concurrentes medidos: 20
- total error rate: 0.0
- p50: 589.4939 ms
- p95: 627.6891 ms
- p99: 635.824 ms
- duplicate order rows: 0
- duplicate response mismatch: 0
- duplicate order errors: 0
- unique order errors: 0
- negative balances: 0

Los 5 requests simultaneos con la misma `Idempotency-Key` devolvieron el mismo `order_id`.

## Verificacion ejecutada

- `python scripts\concurrency_local.py --env-file .env.local.example --searches 10 --duplicate-requests 5 --unique-orders 5 --run-id owner_concurrency_audit_d`: OK
- `python scripts\run_slice_11_tests.py`: OK
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_order_creation.py apps\api\tests\test_hardening_local.py -q`: 16 passed, 1 warning
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 92 passed, 1 warning
- `foreach ($i in 0..11) { python scripts\run_slice_{0:D2}_tests.py }`: OK
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps/api scripts`: OK

## Riesgos residuales

- No se ejecuto stress completo 25/50/100 ni dataset contractual maximo.
- No se conecto Supabase/PostgreSQL real.
- No se conecto Redis cloud real.
- No se conecto storage privado real externo.
- No se verifico Stripe live ni Telegram real.
- No hay deploy/staging real.
- Warning Starlette/httpx sigue aceptado temporalmente.

## Decision

`slice_11_hardening_deploy` queda aceptado en fase local hardening.

El siguiente paso gobernado es decidir entre:

- ejecutar stress local ampliado 25/50/100 en esta PC o en una ventana dedicada, o
- preparar fase externa/staging con Supabase, Redis cloud, storage real, Stripe test mode y Telegram real.

`READY_FOR_REAL_USE` sigue prohibido hasta completar servicios reales, deploy/staging, monitoreo, backup/restore y prueba controlada aprobada por owner.
