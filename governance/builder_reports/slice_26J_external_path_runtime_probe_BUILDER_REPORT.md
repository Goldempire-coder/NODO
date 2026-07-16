# slice_26J_external_path_runtime_probe

Estado final: `READY_FOR_OWNER_REVIEW`

## Decision

`EXTERNAL_PATH_PROBE_TOOLING_HARDENED_WITH_LIMITS`

Construí solo tooling/tests para que las próximas corridas staging separen mejor ruido de setup vs carga medida y permitan variar explícitamente el pool HTTP del harness.

No hice deploy, no cambié infraestructura, no toqué backend de producto, frontend, DB, migraciones, reglas de negocio ni workers.

## Contexto

La evidencia 26I reprodujo un `599` en `mixed c50`:

- endpoint: `GET /api/v1/ads/search`
- exception class: `ConnectError`
- message redacted: `All connection attempts failed`
- `response_started=false`
- elapsed: `21129.5656 ms`

También mostró que el setup remoto del harness genera ruido operativo: aunque el modo se llamaba `db_seed_api_remote`, los anuncios todavía se crean mediante API y disparan invalidaciones/logs antes de la carga medida.

## Cambios realizados

- `scripts/capacity_real.py`
  - Agrega `--max-connections`.
  - Permite fijar explícitamente `httpx.Limits(max_connections=..., max_keepalive_connections=...)`.
  - Separa `phase_timings.setup_seconds`, `phase_timings.measured_load_seconds`, `phase_timings.invariants_seconds` y `phase_timings.total_seconds`.
  - Calcula `metrics.duration_seconds` desde el inicio de carga medida, no desde el inicio del setup.
  - Declara el modo remoto como `hybrid_direct_db_seed_plus_api_ad_creation` para no fingir que el setup es DB puro.
  - Clasifica `httpx.ConnectError` como `CONNECT_ERROR`.

- `apps/api/tests/test_staging_validation_tooling.py`
  - Agrega test de `ConnectError -> CONNECT_ERROR`.
  - Agrega test de `max_connections` explícito.
  - Agrega test de separación setup/load.
  - Actualiza el contrato de fixture mode remoto para reflejar setup híbrido real.

## Validaciones

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - `45 passed, 1 warning`
- `python -m pytest apps\api\tests -q --tb=short`
  - `242 passed, 1 warning`
- `python -m ruff check scripts\capacity_real.py apps\api\tests\test_staging_validation_tooling.py`
  - `All checks passed!`
- `python -m ruff check apps\api scripts`
  - `All checks passed!`
- `python -m compileall scripts\capacity_real.py apps\api\tests\test_staging_validation_tooling.py`
  - OK

## Qué no hice

- No repetí stress staging después del cambio.
- No cambié Railway/Supabase/Upstash/Cloudflare.
- No subí pool/workers/planes.
- No cambié endpoints de producto.
- No declaré `READY_FOR_REAL_USE`.

## Riesgos pendientes

- El harness todavía usa API para crear anuncios en setup. Ahora está declarado, pero una fase posterior debería construir setup DB puro o fixture reuse si el objetivo es medir runtime sin ruido.
- `CONNECT_ERROR` apunta a camino cliente/red/edge/harness, pero falta comparar desde un runner cercano a Railway.
- Las rutas de confirmación en mixed muestran picos externos altos aunque backend process es mucho menor; falta separar por ubicación del runner.

## Siguiente paso recomendado

Ejecutar `mixed c50` con el nuevo `--max-connections` en dos variantes comparables:

1. `--max-connections 50`
2. `--max-connections 200`

Luego comparar:

- `request_error_summary`
- `CONNECT_ERROR` count
- external p95/p99
- backend p95/p99
- `external_minus_backend`
- `phase_timings.setup_seconds` vs `measured_load_seconds`

Si el `CONNECT_ERROR` desaparece al subir conexiones del cliente, el cuello es del harness/client connection pool. Si persiste, medir desde un runner cloud cercano antes de tocar producto o infraestructura.
