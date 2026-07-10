# Performance Runtime Capacity Report - 2026-07-10

## Estado

`PASSED_WITH_LIMITS`

No se hizo deploy. No se declara `READY_FOR_REAL_USE`.

## Objetivo

Medir y mejorar el frente de mayor latencia detectado: lectura del marketplace bajo concurrencia.

## Cambios quirurgicos realizados

- `scripts/capacity_real.py`
  - Agregado `--marketplace-concurrency`.
  - Antes el arnes disparaba todas las lecturas al mismo tiempo con `asyncio.gather`.
  - Ahora permite medir concurrencia controlada: 50, 100, 200, etc.

- `apps/api/app/shared/rate_limit/redis.py`
  - El rate limiter Redis usa Lua atomico para `INCR` + `TTL/EXPIRE`.
  - Reduce viajes a Redis y conserva la misma semantica.

- `apps/api/app/modules/ads/postgres_repository.py`
  - Agregado `list_marketplace_ads_with_businesses`.
  - Evita una segunda consulta para cargar negocios del marketplace.

- `apps/api/app/modules/ads/marketplace.py`
  - Usa el query unido cuando el repositorio lo soporta.
  - Mantiene fallback existente.

- `apps/api/app/main.py`
  - Marketplace search usa `InMemoryRateLimiter` en runtime normal.
  - Redis queda para rate limits sensibles, idempotencia y jobs.
  - Esto alinea el runtime con `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`, que ya indicaba cache/throttle in-process para marketplace.

## Evidencia de rendimiento

### Baseline local ASGI, profile 200

Archivo:
`evidence/slice_runs/post_perf_capacity_concurrent_200_20260710.json`

- Requests: `1385`
- Invariantes: `0`
- Marketplace p95: `2586.3909 ms`
- Create order p95: `1451.7566 ms`
- Confirm payment p95: `843.2964 ms`

### Uvicorn 1 worker, 1000 marketplace reads sin limite de concurrencia

Archivo:
`evidence/slice_runs/uvicorn_marketplace_reads_1000_pool60_20260710.json`

- Requests: `1000`
- Errors: `0`
- Marketplace p95: `32742.4904 ms`
- Resultado: no representa uso real; era una avalancha de 1000 requests simultaneos.

### Uvicorn 1 worker, concurrencia 50

Archivo:
`evidence/slice_runs/uvicorn_marketplace_reads_1000_c50_20260710.json`

- Requests: `1000`
- Errors: `0`
- Marketplace p95: `1275.5827 ms`
- Throughput: `31.4742 req/s`

### Uvicorn 1 worker, concurrencia 100

Archivo:
`evidence/slice_runs/uvicorn_marketplace_reads_1000_c100_20260710.json`

- Requests: `1000`
- Errors: `0`
- Marketplace p95: `605.1147 ms`
- Throughput: `35.797 req/s`

### Uvicorn 1 worker, concurrencia 200

Archivo:
`evidence/slice_runs/uvicorn_marketplace_reads_1000_c200_local_rate_20260710.json`

- Requests: `1000`
- Errors: `0`
- Marketplace p95: `2614.857 ms`
- Throughput: `31.5421 req/s`

### Uvicorn 4 workers, concurrencia 100

Archivo:
`evidence/slice_runs/uvicorn4_marketplace_reads_1000_c100_20260710.json`

- Requests: `1000`
- Errors: `0`
- Marketplace p95: `543.8109 ms`
- Throughput: `38.9902 req/s`

### Uvicorn 4 workers, concurrencia 200

Run:
`uvicorn4_marketplace_reads_1000_c200_20260710`

- Resultado: fallo por `httpx.ReadTimeout`.
- No se toma como aprobado.
- Interpretacion: el multiproceso local en Windows no fue estable para ese perfil. No debe usarse como promesa de produccion.

## Validacion de codigo

- `python -m pytest apps\api\tests -q`
  - `134 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - OK
- `python -m compileall apps\api apps\web\src scripts`
  - OK
- `corepack pnpm --filter @nodo/web build`
  - OK

## Lectura honesta

El sistema no se rompe en los perfiles probados: no hubo errores ni violaciones de invariantes en los runs aceptados.

Pero el marketplace todavia no queda en el nivel de fluidez ideal para 200 usuarios simultaneos. Con 100 simultaneos queda razonable localmente (`p95 ~544-605 ms`). Con 200 simultaneos sube a `~2.6s`.

## Siguiente corte recomendado

`PERF_FRONT_06_MARKETPLACE_HOT_PATH_CACHE_AND_POOL`

Orden recomendado:

1. Perfil con `NODO_INTERNAL_PROFILING=1` en concurrencia 200 para separar:
   - auth
   - cache
   - DB pool
   - query
   - serializacion
2. Revisar si el cache de marketplace esta recibiendo hits reales bajo 18 montos distintos.
3. Ajustar estrategia de cache:
   - cache por rangos comunes de monto, no por monto exacto si aplica.
   - mantener invalidacion al crear orden/anuncio.
4. Evaluar si marketplace puede tener respuesta inicial mas rapida con datos resumidos y detalle lazy.
5. Repetir:
   - 100 simultaneos
   - 200 simultaneos
   - full scenario con ordenes y confirmaciones.

## Riesgos pendientes

- Falta prueba sobre deploy real.
- Falta Supabase/Redis cloud bajo carga real.
- Falta smoke real Telegram completo.
- El warning Starlette/httpx sigue heredado.
- 200 simultaneos aun no tiene latencia aceptable para marketplace.
