# Performance runtime capacity report 02 - 2026-07-10

## Estado

PARTIAL_PASS_WITH_SCALABILITY_FINDINGS

No se hizo deploy. No se declaro READY_FOR_REAL_USE.

## Cambios aplicados

- `apps/api/app/shared/rate_limit/redis.py`
  - Rate limit Redis paso a operacion atomica con Lua.
- `apps/api/app/modules/ads/postgres_repository.py`
  - Marketplace ahora puede traer anuncios y negocios en una sola consulta.
- `apps/api/app/modules/ads/marketplace.py`
  - Marketplace usa la consulta optimizada cuando existe.
- `apps/api/app/main.py`
  - Marketplace read usa limiter/cache in-memory para evitar latencia Redis por lectura publica.
  - Se agrego configuracion de thread limit via lifespan.
  - Se agrego cache runtime corto para usuarios autenticados, apagado en tests.
- `apps/api/app/auth/dependencies.py`
  - Cache corto de usuario autenticado para runtime normal.
- `scripts/capacity_real.py`
  - Stress de marketplace acepta concurrencia configurable y HTTP connection pool alineado a la concurrencia.
- `.env.example`, `.env.local.example`, `.env.staging.example`
  - Agregados/ajustados `API_THREAD_LIMIT`, `AUTH_USER_CACHE_TTL_SECONDS`, `MARKETPLACE_CACHE_TTL_SECONDS`.
- `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`
  - Documentadas las variables de performance y advertencia operacional.

## Validacion funcional

- `python -m pytest apps\api\tests -q`: 134 passed, 1 warning conocido Starlette/httpx.
- `python -m ruff check apps\api scripts`: OK.
- `python -m compileall apps\api apps\web\src scripts`: OK.
- `corepack pnpm --filter @nodo/web build`: OK.

## Hallazgos de stress

### Marketplace reads, single worker, c100

Archivo:

- `evidence/slice_runs/uvicorn1_noaccess_marketplace_1000_c100_20260710.json`

Resultado:

- Requests: 1000
- Errores: 0
- p50: 698.5295 ms
- p95: 3468.7504 ms
- p99: 5458.7896 ms

### Marketplace reads, single worker, c200

Archivo:

- `evidence/slice_runs/uvicorn_authcache_marketplace_1000_c200_20260710.json`

Resultado:

- Requests: 1000
- Errores: 0
- p50: 1610.4741 ms
- p95: 6329.471 ms
- p99: 8184.0456 ms

### Marketplace reads, 4 workers, pool incorrecto

Archivo/log:

- `evidence/slice_runs/uvicorn4_runtime_8011.err.log`

Resultado:

- Fallo por saturacion de conexiones Postgres local.
- Error exacto: `FATAL: sorry, too many clients already`.
- Causa: `NODO_DB_POOL_MAX_SIZE` se multiplica por cantidad de workers. Pool 80 con 4 workers puede intentar hasta 320 conexiones.

### Marketplace reads, 4 workers, pool controlado c100

Archivo:

- `evidence/slice_runs/uvicorn4_pool20_marketplace_1000_c100_20260710.json`

Resultado:

- Requests: 1000
- Errores: 0
- p50: 688.2516 ms
- p95: 3694.6555 ms
- p99: 5812.9037 ms

## Diagnostico

El sistema no se rompe en c100/c200 de lectura de marketplace con single worker: no hubo errores ni invariantes rotas. Pero la latencia todavia no esta donde debe estar para una app fluida bajo picos.

El query principal del marketplace no es el problema actual. Con una base local ya crecida:

- `users`: 8602
- `businesses`: 1263
- `ads`: 16303
- `orders`: 5171
- `credits_ledger`: 17905

El `EXPLAIN ANALYZE` del query de marketplace con filtros reales dio aproximadamente:

- Execution Time: 3.598 ms

El cuello visto en profiling esta antes o alrededor del request completo:

- Auth por usuario unico puede tardar 5 ms a 90 ms bajo concurrencia.
- El endpoint es sincronico y depende del threadpool.
- Con muchos usuarios unicos a la vez, el sistema encola trabajo aunque el query de marketplace este indexado.
- Subir workers sin limitar pool por worker puede tumbar Postgres local.

## Riesgos

- `AUTH_USER_CACHE_TTL_SECONDS=2` mejora navegacion repetida por usuario, pero puede retrasar hasta 2 segundos que un bloqueo/suspension se refleje en runtime. En tests esta apagado para no esconder fallos.
- `MARKETPLACE_CACHE_TTL_SECONDS=30` es seguro para datos calientes porque el cache se limpia al crear/editar/pausar/archivar anuncios y al crear orden, pero no resolvio por si solo el p95 de usuarios unicos.
- Multi-worker requiere plan de conexiones por worker. No se puede subir workers y pool a la vez sin calcular limites.

## Recomendacion siguiente

No seguir subiendo concurrencia a c500/c1000 todavia.

Siguiente corte quirurgico recomendado:

1. Crear una ruta de autenticacion liviana solo para lecturas no sensibles de marketplace, o un cache de sesion/usuario con invalidacion cuando admin bloquea/suspende.
2. Mantener autenticacion completa por DB para mutaciones: crear orden, reportar pago, negocio, creditos, admin, soporte y chat.
3. Definir presupuesto runtime por ambiente:
   - workers
   - pool por worker
   - thread limit por worker
   - max connections de Postgres/Supabase
4. Repetir stress:
   - c100 marketplace
   - c200 marketplace
   - c100 flujo mixto: buscar, detalle, crear orden, instrucciones, reportar pago.

## Conclusion

NODO esta correcto en reglas e invariantes bajo estas pruebas, pero aun no esta optimizado para picos grandes de usuarios unicos leyendo marketplace al mismo tiempo. El siguiente arreglo no debe ser visual ni de features: debe ser una decision de arquitectura de auth/cache para lecturas no sensibles y una configuracion responsable de workers/pool.
