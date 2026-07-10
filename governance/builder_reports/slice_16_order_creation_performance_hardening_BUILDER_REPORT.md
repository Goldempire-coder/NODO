# BUILDER_REPORT - slice_16_order_creation_performance_hardening

## Estado final

READY_FOR_OWNER_REVIEW

No se declara READY_FOR_REAL_USE.

## Resumen

Se optimizo quirurgicamente `POST /api/v1/orders` bajo concurrencia sin cambiar reglas de negocio ni debilitar seguridad.

Cambios principales:

- Instrumentacion interna por etapa para order create cuando `NODO_INTERNAL_PROFILING=1`.
- Idempotency store instrumentado para medir lock/store/replay.
- Lectura compuesta Postgres para ad + business + payment method + active order count.
- Invalidacion marketplace optimizada: version bump compartido + limpieza L1 local, sin full Redis scan/delete por cada orden creada.
- Harness ajustado para ejecutar duplicate idempotency race c25 real.

## Archivos modificados

- `apps/api/app/modules/orders/create_order_flow.py`
- `apps/api/app/modules/orders/postgres_create_order.py`
- `apps/api/app/modules/orders/remitter_routes.py`
- `apps/api/app/shared/cache.py`
- `apps/api/app/shared/idempotency/store.py`
- `apps/api/tests/test_order_creation.py`
- `scripts/capacity_real.py`

## Artefactos creados

- `governance/builder_reports/slice_16_order_creation_performance_hardening_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_16_order_creation_performance_hardening_evidence.md`
- `evidence/slice_runs/slice_16_order_creation_performance_hardening_test_results.json`
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

## Reglas preservadas

- Auth fuerte de `POST /api/v1/orders`.
- `ads.status: active -> in_order`.
- `orders.status = waiting_payment`.
- Snapshot privado de instrucciones de pago.
- `order_state_events`.
- Audit events obligatorios.
- Idempotencia y same-ad race protection.
- Crear orden no consume creditos.
- No se expone `account_value`, `storage_path`, SQL, tokens ni secretos.

## Que NO se construyo

- No se toco frontend de producto.
- No se tocaron payment reports.
- No se tocaron business/admin.
- No se tocaron chat/disputes.
- No se tocaron bots.
- No se cambio lifecycle de ordenes/anuncios/creditos/disputas.
- No se hizo deploy.

## Validaciones ejecutadas

- `python -m pytest apps\api\tests -q`: 138 passed, 1 warning.
- `python -m ruff check apps\api scripts`: passed.
- `python -m compileall apps\api apps\web\src scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- `python scripts\apply_local_migrations.py --env-file .env.local.example --reset --output evidence\slice_runs\slice_16_migrations.json`: passed.
- `python scripts\validate_local_schema.py --env-file .env.local.example --output evidence\slice_runs\slice_16_schema_pre.json`: passed after rerun; first parallel attempt raced with reset and hit transient OID error.
- `python scripts\validate_local_schema.py --env-file .env.local.example --output evidence\slice_runs\slice_16_schema_post.json`: passed.
- Frontend source/build scan for secrets/private fields/claims: passed.
- Log scan for `too many clients`, `ReadTimeout`, `ReadError`, `OperationalError`, `RATE_LIMITED`, `DB_POOL_SATURATED`, HTTP 500: passed.

## Stress ejecutado

| Perfil | Requests | Errors | Error rate | Duration | Throughput | p50 | p95 | p99 | Invariantes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| order-create distinct c25 | 25 | 0 | 0.0 | 2.352s | 10.6287/s | 252.7032ms | 267.0538ms | 268.5277ms | 0 |
| order-create distinct c50 | 50 | 0 | 0.0 | 4.130s | 12.1054/s | 497.3998ms | 516.2397ms | 522.0869ms | 0 |
| order-create distinct c100 | 100 | 0 | 0.0 | 7.870s | 12.7061/s | 719.4509ms | 757.5213ms | 768.2331ms | 0 |
| same-ad race c50 + duplicate idempotency c25 | 75 | 49 expected 409 | 0 real invariant errors | 2.696s | 27.8226/s | 263.8703ms | 298.2876ms | 302.9865ms | 0 |
| mixed c100 | 670 | 73 expected 409 | 0 real invariant errors | 10.744s | 62.3628/s | 189.1803ms | 444.3592ms | 492.2385ms | 0 |

Mixed c100:

- Marketplace reads: 500/500 `200`, p95 326.4167ms.
- Order create distinct: 50/50 `201`, p95 498.9728ms.
- Same-ad race: one `201`, 49 expected `409`, one DB row.
- Duplicate idempotency: 25/25 `201`, same order id, one DB row.
- Payment confirm distinct: 20/20 `200`.
- No negative balances, no double credit consumption.

## Instrumentation evidence

Mixed c100 order profile p95:

- `auth:get_user_by_id`: 17.0631ms.
- `idempotency:get_or_lock`: 97.9632ms.
- `db_reads:order_create_context`: 60.6949ms.
- `transaction:create_order_and_move_ad`: 75.7654ms.
- `cache:marketplace_invalidation`: 8.2189ms.
- `audit:order_created_and_ad_moved`: 44.3538ms.

## Riesgos residuales

- Esta es evidencia local con Docker Postgres/Redis y ASGI harness; no prueba cloud real.
- No se declara capacidad 10,000 ni readiness real.
- Las corridas redirigidas por PowerShell devolvieron exit code 1 aunque los JSON del harness tienen `exit_code: 0`; se reporta como riesgo de harness/shell, no como fallo de backend.

## Confirmaciones

- No debilite auth de `POST /api/v1/orders`.
- No use auth liviana en ordenes.
- No cambie reglas de lifecycle.
- No toque frontend de producto.
- No toque payment reports, business/admin, chat, disputes ni bots.
- No hice deploy.
- No declare READY_FOR_REAL_USE.
