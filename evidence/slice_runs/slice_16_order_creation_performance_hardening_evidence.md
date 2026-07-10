# slice_16_order_creation_performance_hardening Evidence

Estado: READY_FOR_OWNER_REVIEW

## Scope ejecutado

- Se optimizo solo el runtime de `POST /api/v1/orders`.
- Se mantuvo auth fuerte para ordenes.
- Se mantuvo idempotencia, race protection, `active -> in_order`, `waiting_payment`, state events, audit y no consumo de creditos al crear orden.
- No se tocaron frontend, payment reports, business/admin, chat, disputes, bots ni deploy.

## Cambios tecnicos verificados

- `apps/api/app/modules/orders/create_order_flow.py`: instrumentacion por etapas y uso de contexto compuesto cuando el repo lo soporta.
- `apps/api/app/modules/orders/postgres_create_order.py`: lectura compuesta de ad + business + payment method + active order count.
- `apps/api/app/shared/cache.py`: invalidacion marketplace por version bump compartido y limpieza L1 local, sin full scan/delete de Redis por cada orden.
- `apps/api/app/shared/idempotency/store.py`: profiling de store/lock/replay de idempotencia.
- `apps/api/app/modules/orders/remitter_routes.py`: perfil de dependencia auth adjunto solo con `NODO_INTERNAL_PROFILING=1`.
- `scripts/capacity_real.py`: duplicate idempotency race permite c25 real.
- `apps/api/tests/test_order_creation.py`: test de etapas de profiling para order create.

## Evidencia generada

- `evidence/slice_runs/slice_16_migrations.json`
- `evidence/slice_runs/slice_16_schema_pre.json`
- `evidence/slice_runs/slice_16_schema_post.json`
- `evidence/slice_runs/slice_16_order_create_c25.json`
- `evidence/slice_runs/slice_16_order_create_c25.log`
- `evidence/slice_runs/slice_16_order_create_c50.json`
- `evidence/slice_runs/slice_16_order_create_c50.log`
- `evidence/slice_runs/slice_16_order_create_c100.json`
- `evidence/slice_runs/slice_16_order_create_c100.log`
- `evidence/slice_runs/slice_16_order_race_c50_duplicate_c25.json`
- `evidence/slice_runs/slice_16_order_race_c50_duplicate_c25.log`
- `evidence/slice_runs/slice_16_mixed_c100.json`
- `evidence/slice_runs/slice_16_mixed_c100.log`
- `evidence/slice_runs/slice_16_order_creation_performance_hardening_test_results.json`

## Stress results

| Perfil | Requests | Errors | Error rate | Duration | Throughput | p50 | p95 | p99 | Resultado |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| order-create distinct c25 | 25 | 0 | 0.0 | 2.352s | 10.6287/s | 252.7032ms | 267.0538ms | 268.5277ms | PASSED |
| order-create distinct c50 | 50 | 0 | 0.0 | 4.130s | 12.1054/s | 497.3998ms | 516.2397ms | 522.0869ms | PASSED |
| order-create distinct c100 | 100 | 0 | 0.0 | 7.870s | 12.7061/s | 719.4509ms | 757.5213ms | 768.2331ms | PASSED |
| same-ad race c50 + duplicate idempotency c25 | 75 | 49 expected 409 | 0 real invariant errors | 2.696s | 27.8226/s | 263.8703ms | 298.2876ms | 302.9865ms | PASSED |
| mixed c100 | 670 | 73 expected 409 | 0 real invariant errors | 10.744s | 62.3628/s | 189.1803ms | 444.3592ms | 492.2385ms | PASSED |

Mixed c100 details:

- marketplace reads: 500/500 `200`, p95 326.4167ms.
- order create distinct: 50/50 `201`, p95 498.9728ms.
- same-ad race: one `201`, 49 expected `409`, one DB row.
- duplicate idempotency: 25/25 `201`, same order id, one DB row.
- payment confirm distinct: 20/20 `200`.
- invariant violations: 0.

## Profiling mixed c100 order stages

- auth get user by id p95: 17.0631ms.
- idempotency get/lock p95: 97.9632ms.
- DB reads composed context p95: 60.6949ms.
- transaction create order and move ad p95: 75.7654ms.
- marketplace cache invalidation p95: 8.2189ms.
- audit order created/ad moved p95: 44.3538ms.

## Log scan

Patrones buscados:

- `too many clients`
- `ReadTimeout`
- `ReadError`
- `OperationalError`
- `RATE_LIMITED`
- `DB_POOL_SATURATED`
- HTTP status `500`

Resultado: sin hallazgos reales. El scan bruto de `500` genero falsos positivos por conteos y p99; el scan exacto de status `500` no encontro matches.

## Validaciones

- `python -m pytest apps\api\tests -q`: 138 passed, 1 warning.
- `python -m ruff check apps\api scripts`: passed.
- `python -m compileall apps\api apps\web\src scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- Schema pre/post stress: passed.
- Frontend source/build scan: passed, sin secrets, `storage_path`, `account_value` ni claims prohibidos.

## Riesgos residuales

- Los resultados son local ASGI + Docker Postgres/Redis, no prueba cloud real.
- No se declara capacidad para 10,000 usuarios ni `READY_FOR_REAL_USE`.
- El shell PowerShell devolvio exit code 1 en corridas redirigidas aunque los JSON de harness tienen `exit_code: 0`; no hubo fallos reales en payload ni invariantes.
