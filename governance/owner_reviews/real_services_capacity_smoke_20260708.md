# REAL_SERVICES_CAPACITY_SMOKE - 2026-07-08

## Estado

```txt
FUNCTIONAL_SMOKE_PASSED_WITH_PERFORMANCE_BLOCKER
NOT_READY_FOR_REAL_USE
```

## Objetivo

Validar que NODO ya puede hablar con servicios reales de staging:

- Supabase/PostgreSQL real.
- Redis real.
- Schema real migrado.
- Harness de marketplace, ordenes, carreras e idempotencia usando backend local contra servicios cloud.

No fue deploy real de API. La API corrio localmente y conecto contra servicios reales.

## Validacion inicial de servicios reales

Comando:

```txt
python scripts\validate_local_schema.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --output evidence\slice_runs\staging_real_schema_validation_20260708.json
```

Resultado:

- tablas: `25`
- indices: `142`
- Redis ping: `True`
- failures: `[]`
- exit_code: `0`

## Primer smoke real

Run:

```txt
staging_real_smoke_20260708221610
```

Resultado:

```txt
FAILED_BY_FIXTURE_SIZE
```

Motivo:

- `fixture_insufficient_reserved_ads = 1`
- El dataset fue demasiado pequeno para cubrir ordenes distintas, carrera same-ad, idempotency y payment-confirm.
- No fue un fallo de regla de negocio ni de DB.

Dato importante:

- Marketplace p95 ya salio alto: `9570.8619ms`

Cleanup:

```txt
cleanup_execute_staging_real_smoke_20260708221610.json
exit_code = 0
```

## Segundo smoke real

Run:

```txt
staging_real_smoke2_20260708221858
```

Targets:

- businesses: `5`
- ads_per_business: `4`
- remitters: `8`
- marketplace_reads: `20`
- order_creates: `5`
- same_ad_race_requests: `5`
- payment_confirms: `5`

Resultado funcional:

- exit_code: `0`
- total requests: `45`
- total errors: `8`
- Los errores fueron carreras esperadas `409`.

Metricas:

- duration: `185.995s`
- throughput: `0.2419 req/s`
- p50: `6316.016ms`
- p95: `10319.4539ms`
- marketplace p95: `10332.8814ms`
- create order p95: `6481.4201ms`
- confirm payment p95: `4832.1392ms`

Invariant violations:

- `marketplace_read_errors`: `0`
- `order_create_errors`: `0`
- `same_ad_success_count_invalid`: `0`
- `same_ad_unexpected_status`: `0`
- `same_ad_db_rows_invalid`: `0`
- `duplicate_idempotency_response_mismatch`: `0`
- `duplicate_idempotency_db_rows_invalid`: `0`
- `fixture_insufficient_reserved_ads`: `0`
- `payment_report_setup_errors`: `0`
- `confirm_distinct_errors`: `0`
- `confirm_distinct_state_invalid`: `0`
- `confirm_same_order_success_count_invalid`: `0`
- `confirm_same_order_double_consume`: `0`
- `negative_balances`: `0`
- `double_credit_consumption`: `0`
- `db_errors`: `0`

Estados criticos validados:

- Same-ad race: `1` orden creada, resto `409`.
- Idempotency duplicate: todas las respuestas devuelven el mismo order id, `db_rows = 1`.
- Payment confirm distinct: `5/5` confirmadas.
- Same-order confirm race: `1` confirmacion exitosa, resto `409`.
- Consume rows para carrera same-order: `1`.
- Ad status tras confirmacion: `archived`.

Cleanup:

```txt
cleanup_execute_staging_real_smoke2_20260708221858.json
exit_code = 0
```

Schema post-smoke:

```txt
staging_real_schema_validation_post_smoke2_20260708.json
tables = 25
indexes = 142
redis_ping = True
failures = []
exit_code = 0
```

## Corte quirurgico aplicado

Se revisaron las lineas antes de tocar codigo.

Archivo afectado:

```txt
apps/api/app/auth/dependencies.py
```

Hallazgo:

- `require_current_user` y `require_authenticated_user` estaban declaradas como dependencias `async`.
- Dentro de esas dependencias se ejecutaba una lectura sincronica a DB:

```txt
request.app.state.user_repository.get_user_by_id(...)
```

Problema:

- Bajo concurrencia, esa lectura sincronica se ejecutaba dentro del event loop.
- Eso serializaba/frenaba requests concurrentes, especialmente `GET /api/v1/ads/search`.

Cambio:

- `require_authenticated_user` y `require_current_user` pasaron a dependencias sincronicas.
- FastAPI las ejecuta en threadpool y la lectura DB ya no bloquea el event loop.
- No se cambiaron endpoints, payloads, reglas de negocio, RBAC, estados ni respuestas esperadas.

Validacion comparativa de marketplace real:

Antes del corte:

```txt
run_id = staging_real_marketplace_pool50_20260708223453
scenario = marketplace-reads
requests = 20
errors = 0
p50 = 8333.6869ms
p95 = 8545.4671ms
p99 = 8548.413ms
```

Despues del corte:

```txt
run_id = staging_real_marketplace_syncauth_20260708223829
scenario = marketplace-reads
requests = 20
errors = 0
p50 = 2472.4329ms
p95 = 2636.1044ms
p99 = 2677.2402ms
```

Cleanup de ambos runs:

```txt
cleanup_execute_staging_real_marketplace_pool50_20260708223453.json
exit_code = 0

cleanup_execute_staging_real_marketplace_syncauth_20260708223829.json
exit_code = 0
```

Schema post-corte:

```txt
staging_real_schema_validation_post_syncauth_20260708.json
tables = 25
indexes = 142
redis_ping = True
failures = []
exit_code = 0
```

Pruebas post-corte:

```txt
pytest auth + marketplace = 26 passed, 1 warning
pytest completo = 129 passed, 1 warning
ruff = OK
compileall = OK
frontend build = OK
```

## Decision

El smoke funcional contra servicios reales paso. Las reglas de consistencia mas importantes aguantaron:

- no doble orden sobre mismo anuncio;
- no doble consumo de creditos;
- no balances negativos;
- no errores DB;
- carreras devuelven `409`.

El primer cuello real detectado fue corregido con un corte pequeno en auth. La latencia bajo de forma importante, pero todavia no es suficiente para declarar uso real.

## Bloqueo actual

```txt
BLOCKED_BY_REAL_SERVICE_PERFORMANCE
```

Marketplace p95 bajo de `~8.5s` a `~2.6s` en el escenario aislado de 20 lecturas concurrentes. Eso es una mejora real, pero sigue siendo alto para una experiencia fluida.

## Siguiente paso recomendado

1. Perf profiling del read path de marketplace ya sin el bloqueo de auth.
2. Medir por separado auth, Redis rate limit y query marketplace en el mismo run.
3. Evitar otro cambio de rendimiento a ciegas hasta tener tiempos internos por tramo.
4. Repetir smoke real completo.
5. Solo despues correr profile 50/100 cloud.

## Corte de cache marketplace probado

Se implemento un cache corto de marketplace sobre Redis/InMemory:

- TTL default: `5` segundos.
- Key por monto, metodo, delivery, sort, cursor y limit.
- Invalidacion al crear/editar/pausar/archivar anuncios.
- Invalidacion al crear orden o al devolver/expirar anuncio.
- Proteccion local contra stampede por key.

Archivos principales:

```txt
apps/api/app/shared/cache.py
apps/api/app/modules/ads/service.py
apps/api/app/modules/orders/service.py
apps/api/app/main.py
apps/api/app/core/config.py
```

Validacion funcional:

```txt
pytest completo = 131 passed, 1 warning
frontend build = OK
ruff = OK
compileall = OK
schema real post-run = 25 tablas, 142 indices, Redis ping True, failures []
```

Prueba real con cache:

```txt
run_id = staging_real_marketplace_cache_20260708
scenario = marketplace-reads
requests = 20
errors = 0
p50 = 3666.8375ms
p95 = 3866.3452ms
p99 = 3867.2317ms
```

Prueba real con cache + singleflight local:

```txt
run_id = staging_real_marketplace_cache_singleflight_20260708
scenario = marketplace-reads
requests = 20
errors = 0
p50 = 3282.9243ms
p95 = 3982.055ms
p99 = 4050.969ms
```

Conclusion:

- El cache funciona y mantiene consistencia en tests.
- No mejoro el p95 real de marketplace en el escenario concurrente.
- Por tanto, no se cuenta como victoria de performance.
- El cuello restante probablemente esta antes o alrededor del cache: auth DB read, Redis rate limit, red cloud o query marketplace.

Estado despues de este corte:

```txt
BLOCKED_BY_REAL_SERVICE_PERFORMANCE
NOT_READY_FOR_REAL_USE
```

## Perfil interno de marketplace

Se agrego profiling interno temporal bajo:

```txt
NODO_INTERNAL_PROFILING=1
```

El harness ahora captura `_profile` en:

```txt
scripts/capacity_real.py
```

Run con Redis cache:

```txt
run_id = staging_real_marketplace_profiled_20260708
requests = 8
errors = 0
p50 = 3175.2638ms
p95 = 4191.7367ms
```

Promedios internos por etapa:

```txt
service:rate_limit avg = 732.07ms
cache:get_initial avg = 825.71ms
repo:list_marketplace_ads_for_marketplace avg = 359.44ms
repo:get_businesses_by_ids avg = 350.66ms
```

Conclusion:

- La query principal no era el mayor cuello.
- El mayor costo venia de Redis/Upstash en lecturas publicas: rate limit + cache remoto.

## Corte aplicado: cache local de marketplace

Cambio:

- `marketplace_cache` paso de Redis a memoria local por proceso.
- TTL sigue controlado por `MARKETPLACE_CACHE_TTL_SECONDS`.
- Rutas sensibles, idempotencia y jobs siguen usando Redis.

Run:

```txt
run_id = staging_real_marketplace_localcache_profiled_20260708
requests = 8
errors = 0
p50 = 2455.2985ms
p95 = 3099.9689ms
```

Efecto:

- `cache:get_initial` bajo a ~0ms.
- P95 bajo de `4191.7367ms` a `3099.9689ms`.
- Todavia quedaba alto por `service:rate_limit` usando Redis.

Cleanup:

```txt
cleanup_execute_staging_real_marketplace_localcache_profiled_20260708.json
exit_code = 0
```

## Corte aplicado: throttle local solo para marketplace search

Cambio:

- `GET /api/v1/ads/search` usa throttle local por proceso.
- La excepcion queda limitada a lectura publica de marketplace.
- Mutaciones y rutas sensibles siguen usando Redis.

Archivos principales:

```txt
apps/api/app/main.py
apps/api/app/modules/ads/routes.py
apps/api/app/modules/ads/service.py
control_plane/05_SECURITY/RATE_LIMIT_POLICY.md
control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md
```

Run:

```txt
run_id = staging_real_marketplace_localcache_localrate_profiled_20260708
requests = 8
errors = 0
p50 = 1682.6842ms
p95 = 1686.0727ms
```

Perfil interno:

```txt
service:rate_limit = ~0ms
cache:get_initial = ~0ms
repo:list_marketplace_ads_for_marketplace = 255ms-521ms en misses
repo:get_businesses_by_ids = 239ms-298ms en misses
cache hits internos = ~0.06ms
```

Cleanup:

```txt
cleanup_execute_staging_real_marketplace_localcache_localrate_profiled_20260708.json
exit_code = 0
```

Schema post-corte:

```txt
staging_real_schema_validation_post_marketplace_localrate_20260708.json
tables = 25
indexes = 142
redis_ping = True
failures = []
exit_code = 0
```

Pruebas finales:

```txt
pytest completo = 131 passed, 1 warning
frontend build = OK
ruff = OK
compileall = OK
```

## Resultado de rendimiento acumulado

Marketplace real aislado:

```txt
Antes de auth fix:       p95 ~8545ms
Despues auth sync:       p95 ~2636ms
Cache Redis:             p95 ~3866ms-4191ms
Cache local:             p95 ~3099ms
Cache local + rate local p95 ~1686ms
```

Estado actual:

```txt
IMPROVED_BUT_NOT_READY_FOR_REAL_USE
```

El siguiente cuello no esta dentro de la logica de marketplace. El servicio interno ya responde muchas rutas cacheadas en sub-milisegundos, pero el total HTTP sigue alrededor de `1.6s`. El proximo corte debe medir auth/dependency antes del servicio:

```txt
JWT decode
user_repository.get_user_by_id
FastAPI dependency overhead
ASGI/TestClient harness overhead
```

## Perfil de auth/dependency

Se agrego profiling de auth solo bajo:

```txt
NODO_INTERNAL_PROFILING=1
```

El perfil queda adjunto en `data._profile.dependency.auth` solo para medicion interna. No cambia payload normal.

Run:

```txt
run_id = staging_real_marketplace_authprofile_20260708
requests = 8
errors = 0
p50 = 1898.9891ms
p95 = 1901.2513ms
```

Hallazgo:

```txt
auth:decode_access_token = ~0.03ms
auth:get_user_by_id = 1238ms-1396ms en varias requests concurrentes
```

Conclusion:

- El problema no era JWT.
- El problema era lectura de usuario contra Supabase/PostgreSQL con conexiones frias bajo concurrencia.

Cleanup:

```txt
cleanup_execute_staging_real_marketplace_authprofile_20260708.json
exit_code = 0
```

## Corte aplicado: warmup best-effort del pool DB

Cambio:

- Se agrego `warm_pool(database_url, size=NODO_DB_POOL_WARM_SIZE)`.
- En runtime no-test, la API intenta precalentar conexiones al arrancar.
- Si el warmup falla, no tumba el proceso; queda log `db_pool_warm_failed` y `/ready` sigue siendo la autoridad de salud.
- Default documentado: `NODO_DB_POOL_WARM_SIZE=8`.

Archivos principales:

```txt
apps/api/app/shared/db/connection.py
apps/api/app/main.py
.env.example
.env.local.example
.env.staging.example
control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md
```

Run:

```txt
run_id = staging_real_marketplace_dbwarm_authprofile_20260708
requests = 8
errors = 0
p50 = 1002.946ms
p95 = 1090.5429ms
```

Perfil despues de warmup:

```txt
auth:get_user_by_id = ~354ms-427ms
service:rate_limit = ~0ms
cache:get_initial = ~0ms
repo:list_marketplace_ads_for_marketplace = ~272ms-406ms en misses
repo:get_businesses_by_ids = ~317ms-364ms en misses
```

Cleanup:

```txt
cleanup_execute_staging_real_marketplace_dbwarm_authprofile_20260708.json
exit_code = 0
```

Schema post-warmup:

```txt
staging_real_schema_validation_post_dbwarm_marketplace_20260708.json
tables = 25
indexes = 142
redis_ping = True
failures = []
exit_code = 0
```

Pruebas finales post-warmup:

```txt
pytest completo = 131 passed, 1 warning
frontend build = OK
ruff = OK
compileall = OK
```

## Resultado actualizado

Marketplace real aislado:

```txt
Antes de auth fix:              p95 ~8545ms
Despues auth sync:              p95 ~2636ms
Cache local + rate local:       p95 ~1686ms
DB pool warmup:                 p95 ~1090ms
```

Estado actualizado:

```txt
IMPROVED_SIGNIFICANTLY
NOT_READY_FOR_REAL_USE
```

El siguiente cuello medido ya no es Redis ni conexion fria. Lo que queda visible es latencia normal de Supabase/PostgreSQL desde esta PC hacia cloud y dos lecturas DB en los misses de marketplace. El proximo paso correcto es repetir el mismo smoke desde el backend desplegado cerca de Supabase antes de hacer otro corte de codigo.

## Smoke remoto contra Railway

Se desplego la API en Railway y se validaron servicios reales:

```txt
Railway service = nodo-api
URL = https://nodo-api-production.up.railway.app
region inicial = sfo
/health = ok
/ready = database ok, redis ok
```

Se configuraron variables de runtime:

```txt
NODO_DB_POOL_MAX_SIZE=50
NODO_DB_POOL_TIMEOUT_SECONDS=20
NODO_DB_POOL_WARM_SIZE=8
```

Primer benchmark remoto desde esta PC contra Railway en `sfo`:

```txt
run_id = remote_marketplace_railway_20260708
requests = 100
errors = 0
p50 = 1795.9844ms
p95 = 8179.3133ms
p99 = 16113.4835ms
cleanup = execute ok
```

Decision infra aplicada:

```txt
Railway region movida a US East
sfo = 0
us-east = 1
```

Benchmark remoto en `US East`, una replica:

```txt
run_id = remote_marketplace_railway_useast_warm_20260708
requests = 100
errors = 0
p50 = 1011.1261ms
p95 = 7672.743ms
p99 = 7718.3443ms
cleanup = execute ok
```

Escalado horizontal temporal:

```txt
us-east = 2 replicas
```

Benchmark remoto en `US East`, dos replicas:

```txt
run_id = remote_marketplace_railway_useast2_20260708
requests = 100
errors = 0
p50 = 844.4763ms
p95 = 7803.722ms
p99 = 15464.6142ms
cleanup = execute ok
```

Conclusion de estos tres runs:

- Mover Railway a `US East` mejoro p50.
- Dos replicas mejoraron p50 un poco mas.
- p95 del harness local siguio alto.
- No hubo errores HTTP, DB ni invariantes rotas.
- El p95 alto no debe tratarse automaticamente como p95 real del servidor, porque la prueba se ejecuta desde esta PC abriendo muchas conexiones concurrentes hacia Railway.

## Perfil interno del backend desplegado

Se activo profiling temporal solo en staging:

```txt
NODO_INTERNAL_PROFILING=1
```

Run perfilado reducido:

```txt
run_id = remote_marketplace_profiled_20_20260708
requests = 20
errors = 0
p50 cliente = 615.496ms
p95 cliente = 7723.6075ms
cleanup = execute ok
```

Tiempos internos observados dentro de Railway:

```txt
auth:get_user_by_id = ~35ms-82ms
repo:list_marketplace_ads_for_marketplace = ~40ms-69ms en misses
repo:get_businesses_by_ids = ~35ms-72ms en misses
service total = ~32ms-141ms
auth total = ~35ms-82ms
```

Railway metrics para la ventana de prueba:

```txt
2xx = 468
4xx = 0
5xx = 0
error_rate = 0.0
p50 = 161ms
p90 = 161ms
p95 = 161ms
p99 = 161ms
```

Despues del diagnostico se apago profiling:

```txt
NODO_INTERNAL_PROFILING=0
deployment = cf143a0e-95e2-486e-a2d8-caab857df220
status = SUCCESS
/ready = database ok, redis ok
```

Estado actual Railway:

```txt
region = US East
replicas = 2/2 running
```

## Decision actualizada

El backend desplegado no muestra el mismo p95 alto internamente. La evidencia apunta a:

1. Servidor/API: saludable, sin errores, p95 Railway ~161ms en la ventana medida.
2. Harness desde esta PC: p95 alto por conexion/red/localidad/apertura concurrente de conexiones hacia Railway.
3. Codigo de marketplace: internamente medido en ~32ms-141ms por request, incluyendo cache y query cuando aplica.

Estado:

```txt
REMOTE_BACKEND_FUNCTIONAL
SERVER_SIDE_MARKETPLACE_HEALTHY_IN_MEASURED_WINDOW
CLIENT_SIDE_HARNESS_LATENCY_NOT_REPRESENTATIVE
NOT_READY_FOR_REAL_USE
```

Siguiente corte recomendado:

1. No tocar mas codigo de marketplace por ahora.
2. Crear prueba remota mas realista:
   - carga escalonada, no 100 conexiones de golpe desde una sola PC;
   - conexiones reutilizadas;
   - medicion con Railway metrics como fuente primaria server-side;
   - escenarios separados para marketplace, crear orden, reportar pago y confirmar pago.
3. Decidir si se dejan `2` replicas por velocidad o se vuelve a `1` replica para ahorrar mientras seguimos en staging.
