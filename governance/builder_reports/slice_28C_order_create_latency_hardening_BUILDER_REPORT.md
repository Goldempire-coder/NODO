# slice_28C_order_create_latency_hardening - BUILDER_REPORT

Estado final: `READY_FOR_OWNER_REVIEW`

## Objetivo

Reducir el p95 backend de `POST /api/v1/orders` identificado en 28B, sin cambiar infraestructura, planes, workers, pool, reglas de negocio ni contratos publicos.

## Cambios implementados

- `apps/api/app/modules/orders/create_order_flow.py`
  - Mantiene replay idempotente para retries.
  - Evita el precheck SQL persistente de idempotencia en el camino fresco de Postgres.
  - Si la creacion choca con conflicto de anuncio/idempotencia, consulta la orden existente y replayea si corresponde.
  - Si el payload no coincide, conserva `IDEMPOTENCY_PAYLOAD_MISMATCH`.

- `apps/api/app/modules/orders/postgres_create_order.py`
  - Declara `skips_idempotency_precheck_on_create_order = True`.
  - Escribe audit events de `order_created` y `ad_moved_in_order` dentro de la misma transaccion de creacion de orden.
  - Conserva la constraint unica `orders_remitter_idempotency_idx` como proteccion persistente.

- `apps/api/tests/test_order_creation.py`
  - Agrega test de regresion para el contrato interno de Postgres: audit transaccional y precheck omitido en creates frescos.

## Validaciones locales

- `python -m pytest apps\api\tests\test_order_creation.py -q --tb=short`: `15 passed, 1 warning`
- `python -m pytest apps\api\tests -q`: `258 passed, 1 warning`
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Deploy staging

- Build final medido: `staging-28c2-20260711202300`
- Railway deployment ID: `3d204188-2a70-4c67-bb35-7a9466edb065`
- `/version`: `200`
- `/ready`: DB OK, Redis OK

## Resultado cloud

| Corrida | Build | Concurrency | Requests | Status | Order client p95 | Order backend p95 | Errors |
|---|---|---:|---:|---|---:|---:|---:|
| 28B baseline c50 | `staging-28b` | 50 | 200 | `50x 201`, `150x 200` | `987.4062ms` | `571.6427ms` | 0 |
| 28C first variant c50 | `staging-28c` | 50 | 200 | `50x 201`, `150x 200` | `1034.9087ms` | `739.5536ms` | 0 |
| 28C2 final c50 | `staging-28c2` | 50 | 200 | `50x 201`, `150x 200` | `885.12ms` | `456.6227ms` | 0 |
| 28B baseline c100 | `staging-28b` | 100 | 400 | `100x 201`, `300x 200` | `1734.9137ms` | `977.2929ms` | 0 |
| 28C2 final c100 | `staging-28c2` | 100 | 400 | `100x 201`, `300x 200` | `1661.7075ms` | `282.6614ms` | 0 |

## Mejoras medidas

- c50 order backend p95: `571.6427ms -> 456.6227ms`, mejora aproximada `20.1%`.
- c50 order client p95: `987.4062ms -> 885.12ms`, mejora aproximada `10.4%`.
- c100 order backend p95: `977.2929ms -> 282.6614ms`, mejora aproximada `71.1%`.
- c100 order client p95: `1734.9137ms -> 1661.7075ms`, mejora aproximada `4.2%`.

La mejora backend es clara. La mejora cliente es menor porque a c100 sigue existiendo tiempo externo/red/runner fuera del backend medido.

## Stages finales relevantes c100

- `auth:get_user_by_id` p95 `69.5055ms`
- `db_reads:order_create_context` p95 `61.6523ms`
- `transaction:create_order_and_move_ad` p95 `128.232ms`
- `cache:marketplace_invalidation` p95 `11.3947ms`
- `idempotency:get_or_lock` p95 `8.4665ms`
- `rate_limit:order_create` p95 `8.0699ms`

El stage anterior `service:get_existing_idempotency` ya no aparece en el camino normal.

## Cleanup

Cleanup aplicado y verificado para:

- `gha_29173362553_1_mixed-read-order`
- `gha_mixed50_slice28c_fixture_20260711200748`
- `gha_29173633187_1_mixed-read-order`
- `gha_mixed50_slice28c2_fixture_20260711201814`
- `gha_29173933951_1_mixed-read-order`
- `gha_mixed100_slice28c2_fixture_20260711202458`

Verificacion DB posterior: `0` businesses y `0` ads vivos por esos run IDs.

## Riesgos residuales

- La latencia cliente en c100 sigue alta por componente externo/runner/red: marketplace client p95 `3663.8148ms` con backend p95 `30.7362ms`.
- `auth:get_user_by_id`, `db_reads:order_create_context` y la transaccion siguen siendo los principales costos backend de orden.
- No se probo c200 mixed despues de 28C2.
- No se declaro capacidad 10,000 usuarios.

## Confirmacion

- No se cambio infraestructura.
- No se subieron workers, pool, planes ni replicas.
- No se cambio DB schema.
- No se cambiaron reglas de lifecycle, creditos, pagos, disputas ni bots.
- No se declaro `READY_FOR_REAL_USE`.
