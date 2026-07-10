# Performance Hardening Front 03/04 - 2026-07-10

## Estado

PASSED_WITH_RESIDUAL_MARKETPLACE_LATENCY

No hice deploy. No conecte servicios reales nuevos. No declare READY_FOR_REAL_USE.

## Objetivo

Seguir el trabajo de escalabilidad despues de la prueba concurrente 200. El foco fue reducir costo de rutas calientes sin cambiar reglas de producto ni contratos API.

## Cambios quirurgicos

### 1. Rate limit Redis atomico

Archivo:

- `apps/api/app/shared/rate_limit/redis.py`

Cambio:

- `RedisRateLimiter.allow` paso de `pipeline(INCR + TTL) + EXPIRE opcional` a un script atomico de Redis.
- Mantiene la misma regla: el contador vive en Redis y se bloquea cuando supera `max_attempts`.
- Conserva TTL incluso si una llave queda sin expiracion.
- Reintenta cargando script si Redis responde `NOSCRIPT`.

Motivo:

- Reducir viajes a Redis y mantener seguridad centralizada.

Resultado medido:

- No curo marketplace.
- Mejoro algunas rutas mutantes en la corrida completa:
  - crear orden p95 bajo de `1451.7566 ms` a `1375.0857 ms`
  - confirmar pago p95 bajo de `843.2964 ms` a `710.5861 ms`

### 2. Marketplace con una consulta menos

Archivos:

- `apps/api/app/modules/ads/postgres_repository.py`
- `apps/api/app/modules/ads/marketplace.py`

Cambio:

- Agregue `list_marketplace_ads_with_businesses` para Postgres.
- La busqueda del marketplace ahora puede traer anuncio + negocio aprobado en una sola consulta.
- El servicio conserva fallback para repos in-memory/test.
- No cambio payload ni endpoint.

Motivo:

- Antes la ruta leia anuncios y luego hacia otra consulta para negocios.
- Esto era correcto, pero caro bajo concurrencia.

Resultado medido:

- Sonda con profiling:
  - antes: marketplace p95 `159.5112 ms`
  - despues: marketplace p95 `143.9775 ms`
  - desaparece la etapa separada `repo:get_businesses_by_ids`
- Corrida concurrente 200:
  - marketplace p95 bajo de `2586.3909 ms` a `2500.5604 ms`
  - crear orden p95 bajo de `1451.7566 ms` a `1316.463 ms`

## Evidencia de corridas

### Baseline concurrente 200

Archivo:

- `evidence/slice_runs/post_perf_capacity_concurrent_200_20260710.json`

Resultados:

- Total requests: 1385
- Total errors: 73
- Nota: esos errores son los `409` esperados de carreras controladas.
- Marketplace p95: `2586.3909 ms`
- Crear orden p95: `1451.7566 ms`
- Confirmar pago p95: `843.2964 ms`
- Invariantes con falla: ninguna

### Despues de rate limit Lua

Archivo:

- `evidence/slice_runs/post_rate_limiter_lua_capacity_200_20260710.json`

Resultados:

- Marketplace p95: `2670.4996 ms`
- Crear orden p95: `1375.0857 ms`
- Confirmar pago p95: `710.5861 ms`
- Invariantes con falla: ninguna

Lectura:

- Ayuda mutaciones.
- No ayuda suficiente al marketplace.

### Despues de query combinada marketplace

Archivo:

- `evidence/slice_runs/post_marketplace_join_capacity_200_20260710.json`

Resultados:

- Marketplace p95: `2500.5604 ms`
- Crear orden p95: `1316.463 ms`
- Confirmar pago p95: `828.8271 ms`
- Invariantes con falla: ninguna

Lectura:

- Mejora moderada.
- Correctitud sigue intacta.
- Marketplace todavia esta lento bajo 1000 reads simultaneos locales.

### Prueba con pool local mas grande

Archivo:

- `evidence/slice_runs/post_marketplace_join_pool60_reads_20260710.json`

Configuracion temporal:

- `NODO_DB_POOL_MAX_SIZE=60`
- `NODO_DB_POOL_WARM_SIZE=20`

Resultados:

- Marketplace reads: 1000
- Errores: 0
- Marketplace p95: `2179.5156 ms`
- Throughput: `43.4254 req/s`
- Invariantes con falla: ninguna

Lectura:

- Hay cola por recursos compartidos.
- Aumentar pool ayuda, pero no es una solucion magica: en Supabase/Railway hay que dimensionar con cuidado para no saturar conexiones.

## Validacion final

- `python -m pytest apps\api\tests -q`: `134 passed, 1 warning`
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Lectura honesta

La consistencia esta fuerte:

- no se duplican ordenes
- idempotencia aguanta
- carreras por mismo anuncio producen una sola orden
- confirmacion concurrente consume creditos una sola vez
- no hay balances negativos
- no hay errores DB

La velocidad todavia necesita trabajo:

- marketplace bajo 1000 lecturas simultaneas locales sigue sobre 2 segundos p95
- el rate limit Redis y la cola de recursos pesan mucho
- el harness local con `ASGITransport` tambien puede estar amplificando cola, pero no voy a asumirlo como excusa sin prueba remota

## Proximo corte recomendado

PERF_FRONT_05_RUNTIME_CAPACITY_AND_RATE_LIMIT_POLICY

Orden recomendado:

1. Medir endpoint marketplace contra servidor real local `uvicorn`, no solo `ASGITransport`.
2. Comparar:
   - ASGITransport local
   - uvicorn local
   - Railway staging cuando este listo
3. Revisar si marketplace read necesita rate limit menos costoso o por IP/surface con ventana distinta.
4. Revisar pool recomendado por entorno:
   - local Docker
   - Railway backend
   - Supabase Postgres
5. Solo despues decidir si hace falta cache distribuido para marketplace en Redis.

## Riesgos residuales

- No es prueba con Supabase real.
- No es prueba contra deploy real.
- Redis local no representa exactamente Upstash/Redis cloud.
- El p95 de marketplace aun no cumple el nivel que queremos para experiencia premium.
- Warning Starlette/httpx sigue aceptado temporalmente.
