# slice_18B_marketplace_auth_ttl_capacity_review

## Estado

PASSED_WITH_RESIDUAL_LATENCY_RISK

No se declara `READY_FOR_REAL_USE`.

## Objetivo

Reducir lecturas innecesarias a DB en `GET /api/v1/ads/search` cuando el usuario solo esta leyendo marketplace publico-seguro.

## Cambio aplicado

- `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS` pasa de default `30` a `300` segundos.
- Staging Railway queda configurado con `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS=300`.
- El path claims-only sigue limitado a marketplace reads.
- Mutaciones y rutas sensibles siguen usando auth fuerte:
  - crear orden
  - payment instructions
  - report payment
  - chat/disputes
  - business app
  - admin
  - credits
  - bots

## Archivos modificados

- `apps/api/app/core/config.py`
- `apps/api/tests/test_ads_marketplace.py`
- `.env.example`
- `.env.local.example`
- `.env.staging.example`
- `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`

## Validacion local

- Marketplace tests: `21 passed, 1 warning`
- Full API pytest: `171 passed, 1 warning`
- Ruff: OK
- Compileall: OK
- Frontend build: OK

## Validacion staging

Staging API:

- Railway service: online
- Replicas: `2/2`
- Health: OK

### c50

Evidence: `evidence/slice_runs/slice18b_marketplace_ttl300_c50_20260710164414.json`

- Requests: `400`
- Errors: `0`
- p50: `604.7503 ms`
- p95: `1906.8125 ms`
- p99: `7594.0697 ms`
- Auth mode: `400 marketplace_claims`, `0 fallback_db`
- Invariant violations: `0`
- Cleanup: `evidence/slice_runs/slice18b_marketplace_ttl300_c50_20260710164414_cleanup.json`

### c100

Evidence: `evidence/slice_runs/slice18b_marketplace_ttl300_c100_20260710164843.json`

- Requests: `600`
- Errors: `0`
- p50: `1174.9648 ms`
- p95: `5542.6421 ms`
- p99: `8448.9666 ms`
- Auth mode: `600 marketplace_claims`, `0 fallback_db`
- Invariant violations: `0`
- Cleanup: `evidence/slice_runs/slice18b_marketplace_ttl300_c100_20260710164843_cleanup.json`

## Resultado tecnico

El costo innecesario de auth fuerte en marketplace quedo eliminado para la ventana operativa de 5 minutos.

La latencia externa alta en c100 persiste aunque:

- no hay errores
- no hay fallback a DB
- no hay invariantes rotas
- cache local domina los hits

Esto indica que el siguiente cuello probable no esta en la logica interna del endpoint, sino en la ruta externa/runtime/conexiones del harness/Railway antes o alrededor del request medido.

## Riesgo residual

- Con claims-only por 300 segundos, un usuario bloqueado podria seguir leyendo marketplace publico-seguro hasta que venza esa ventana.
- No puede crear orden ni ejecutar acciones sensibles sin auth fuerte.
- El tradeoff se considera aceptable para lectura publica-segura, pero debe mantenerse prohibido para mutaciones.

## Siguiente recomendacion

Separar latencia de:

1. harness/local machine -> Railway
2. Railway edge/router -> app
3. app internal handler

El siguiente corte recomendado es ejecutar el mismo profiling desde un runner cloud cercano o agregar un endpoint/stage de ping interno controlado para medir overhead externo sin tocar DB/cache.
