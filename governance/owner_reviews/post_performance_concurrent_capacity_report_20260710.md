# Post Performance Concurrent Capacity Report - 2026-07-10

## Estado

PASSED_CORRECTNESS_WITH_PERFORMANCE_BOTTLENECK

No hice deploy. No conecte servicios nuevos. No declare READY_FOR_REAL_USE.

## Objetivo

Validar concurrencia realista despues de los indices `0016_query_performance_indexes` y cache corto de dashboard/admin metrics:

- muchos clientes leyendo marketplace al mismo tiempo
- muchos clientes creando ordenes distintas al mismo tiempo
- varios clientes intentando tomar el mismo anuncio al mismo tiempo
- reintentos con la misma idempotency key
- varios negocios confirmando pagos distintos
- varios requests intentando confirmar la misma orden al mismo tiempo

## Corridas ejecutadas

### Calibracion descartada

Archivo:

- `evidence/slice_runs/post_perf_capacity_calibration_20260710.json`

Resultado:

- `exit_code`: 1
- No se toma como falla del sistema.
- Motivo: fixture invalido. Se pidieron mas ordenes de las que permitia el set de anuncios reservados.

### Concurrencia 100

Archivo:

- `evidence/slice_runs/post_perf_capacity_concurrent_100_20260710.json`

Preparacion:

- Negocios: 10
- Anuncios: 180
- Remitters/clientes: 100

Carga:

- Marketplace reads: 500
- Ordenes distintas: 100
- Carrera por el mismo anuncio: 25 requests
- Confirmaciones distintas: 50

Resultado funcional:

- Marketplace read errors: 0
- Order create errors: 0
- Idempotency duplicates invalidos: 0
- Doble consumo de creditos: 0
- Balances negativos: 0
- DB errors: 0
- Invariantes con falla: ninguna

Resultado de carrera:

- Mismo anuncio: 25 intentos, exactamente 1 orden creada y 24 respuestas `409`.
- Misma orden confirmada: 25 intentos, exactamente 1 confirmacion y 24 respuestas `409`.
- Idempotency replay: 10 intentos, misma orden final, 1 fila real.

Performance:

- Total requests: 710
- p95 general: 1500.8288 ms
- Marketplace p95: 1506.4061 ms
- Crear orden p95: 1012.8876 ms
- Confirmar pago p95: 364.1596 ms

### Concurrencia 200

Archivo:

- `evidence/slice_runs/post_perf_capacity_concurrent_200_20260710.json`

Preparacion:

- Negocios: 20
- Anuncios: 360
- Remitters/clientes: 200

Carga:

- Marketplace reads: 1000
- Ordenes distintas: 200
- Carrera por el mismo anuncio: 50 requests
- Confirmaciones distintas: 100

Resultado funcional:

- Marketplace read errors: 0
- Order create errors: 0
- Idempotency duplicates invalidos: 0
- Doble consumo de creditos: 0
- Balances negativos: 0
- DB errors: 0
- Invariantes con falla: ninguna

Resultado de carrera:

- Mismo anuncio: 50 intentos, exactamente 1 orden creada y 49 respuestas `409`.
- Misma orden confirmada: 25 intentos, exactamente 1 confirmacion y 24 respuestas `409`.
- Idempotency replay: todos los intentos devolvieron la misma orden, 1 fila real.

Performance:

- Total requests: 1385
- Throughput: 36.342 req/s
- p50 general: 2522.5088 ms
- p95 general: 2584.3484 ms
- p99 general: 2595.5976 ms
- Marketplace p95: 2586.3909 ms
- Crear orden p95: 1451.7566 ms
- Confirmar pago p95: 843.2964 ms

## Schema post corrida

Archivo:

- `evidence/slice_runs/post_perf_capacity_concurrent_200_schema_post_20260710.json`

Resultado:

- Tablas: 25
- Indices: 154
- Redis ping: OK
- Failures: []

## Validacion final

- `python -m pytest apps\api\tests -q`: 134 passed, 1 warning
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Cambios de harness realizados

No cambie reglas de producto. Ajuste solamente scripts de prueba local:

- `scripts/local_smoke.py`
  - dejo de usar `POST /api/v1/businesses` como fixture porque el self-onboarding ya esta correctamente bloqueado despues de 14B1.
  - ahora crea negocios aprobados como fixture interno local, con access link y metodo de pago aprobado.

- `scripts/stress_local.py`
  - rota multiples remitters para no simular 2000 busquedas con un solo usuario.
  - evita colision entre ids sinteticos de business owners y remitters.

## Lectura honesta

La parte critica de seguridad y consistencia aguanto:

- no se duplicaron ordenes
- no se tomo el mismo anuncio dos veces
- no se consumieron creditos dos veces
- no hubo balances negativos
- no hubo transiciones invalidas
- no hubo errores de DB

Pero la velocidad bajo concurrencia todavia no esta donde debe estar:

- marketplace concurrente llega a p95 de ~2.6 segundos en profile 200
- crear orden llega a p95 de ~1.45 segundos
- confirmar pago llega a p95 de ~843 ms

Esto no significa que el sistema este roto. Significa que el siguiente trabajo no debe ser mas features: debe ser optimizacion quirurgica de rutas calientes.

## Proximo corte recomendado

PERF_FRONT_03_MARKETPLACE_READ_PATH

Orden:

1. Leer `apps/api/app/modules/ads/*` y repositorios usados por `GET /api/v1/ads/search`.
2. Medir donde se va el tiempo: query, serializacion, auditoria, rate limit, conexion DB o fixture local.
3. Optimizar sin cambiar contrato API.
4. Repetir concurrencia 200.
5. Solo despues pasar a `POST /api/v1/orders`.

## Riesgos residuales

- Esta prueba fue local con Docker Postgres/Redis, no Supabase/Redis cloud.
- No fue deploy real.
- No mide latencia de red real.
- Warning Starlette/httpx sigue aceptado temporalmente.
- La app sigue sin READY_FOR_REAL_USE.
