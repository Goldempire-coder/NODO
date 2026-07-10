# Post Performance Profile 100 Stress Report - 2026-07-10

## Estado

PASSED_AFTER_HARNESS_FIXES

## Objetivo

Repetir stress local profile 100 despues de:

- migracion `0016_query_performance_indexes`
- cache TTL corto para read models admin

## Hallazgos durante la prueba

### 1. Harness viejo usaba self-onboarding legacy

El primer intento fallo porque `scripts/local_smoke.py` todavia intentaba crear negocios con `POST /api/v1/businesses`.

Ese flujo esta bloqueado correctamente despues de 14B1 porque el acceso negocio ahora depende de admin/backend + `business_access_links`.

Correccion:

- `scripts/local_smoke.py` ahora crea negocios aprobados por fixture local interno.
- No se reabrio self-onboarding.
- No se cambio producto runtime.

### 2. Harness viejo simulaba un solo cliente haciendo 2000 busquedas

El siguiente intento fallo con `RATE_LIMITED` porque el stress hacia muchas busquedas con un solo remitente.

Correccion:

- `scripts/stress_local.py` ahora usa pool de remitentes.
- Profile 100 usa 100 clientes sinteticos.

### 3. IDs sinteticos de remitentes chocaban con owners

Un intento fallo con `FORBIDDEN` porque un remitente sintetico compartia identidad con un owner de negocio.

Correccion:

- Los remitentes usan rango de IDs separado.
- Ya no se mezclan identidades cliente/negocio.

## Resultado final profile 100

Run:

- `post_perf_profile100_disjoint_users_20260710_010344`

Evidencia:

- `evidence/slice_runs/post_perf_profile100_disjoint_users_20260710_010344.json`
- `evidence/slice_runs/post_perf_profile100_disjoint_users_20260710_010344.checkpoint.json`
- `evidence/slice_runs/post_perf_profile100_disjoint_users_20260710_010344.log`
- `evidence/slice_runs/post_perf_schema_pre_profile100_20260710.json`
- `evidence/slice_runs/post_perf_schema_post_profile100_20260710.json`

Carga ejecutada:

- negocios: 200
- clientes/remitentes sinteticos: 100
- anuncios: 2000
- ordenes: 2000
- ordenes con flujo completo: 200
- busquedas marketplace: 2000
- requests totales: 7302

Metricas:

- errores: 0
- error rate: 0.0
- duration: 529.248 s
- throughput: 13.7969 req/s
- p50: 31.8512 ms
- p95: 41.6392 ms
- p99: 48.4135 ms

Rutas mas lentas:

- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`: p95 74.0538 ms
- `POST /api/v1/orders`: p95 45.1696 ms
- `POST /api/v1/business/orders/{id}/confirm-payment`: p95 43.3455 ms
- `POST /api/v1/orders/{id}/payment-report`: p95 42.3061 ms
- `POST /api/v1/business/ads`: p95 39.9438 ms
- `GET /api/v1/ads/search`: p95 11.213 ms

Invariantes:

- idempotency duplicates: 0
- idempotency replay conflicts: 0
- double credit consumption: 0
- double credit accreditation: 0
- negative balances: 0
- invalid transitions: 0
- Redis failures: 0
- DB errors: 0
- timeouts: 0
- deadlocks: 0
- job lock failures: 0

Schema post:

- tablas: 25
- indices: 154
- Redis ping: OK
- failures: []

## Validacion adicional

- `python -m pytest apps\api\tests -q`: 134 passed, 1 warning
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Conclusion

Profile 100 local paso limpio despues de corregir el harness para representar mejor el modelo actual:

- negocios no se auto-registran
- acceso negocio se siembra como fixture local
- clientes/remitentes se simulan como usuarios separados

El sistema local esta respondiendo bien para esta escala sintetica.

## Pendiente recomendado

1. Ejecutar profile 200 o prueba concurrente real con workers paralelos.
2. Medir contra servicios reales con limites controlados.
3. Separar stress de lectura, stress de ordenes y stress de operaciones negocio para encontrar cuellos de botella por flujo.
4. No declarar `READY_FOR_REAL_USE` hasta pasar smoke real Telegram, Supabase/Redis/Storage reales y deploy controlado.
