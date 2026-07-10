# slice_18C_runtime_latency_isolation_report

## Estado

PASSED_BACKEND_NOT_BOTTLENECK

No se declara `READY_FOR_REAL_USE`.

## Objetivo

Separar el cuello de latencia observado en pruebas remotas:

- app/backend interno
- DB/Redis
- Railway router/runtime
- red local/harness desde la PC

## Cambios realizados

- Agregado `RuntimeTimingMiddleware`.
- Cada respuesta incluye:
  - `X-NODO-Process-Time-Ms`
  - `Server-Timing: app;dur=<ms>`
- Creado `scripts/runtime_latency_probe.py` para medir endpoints livianos sin depender del harness de marketplace.

## Archivos modificados

- `apps/api/app/shared/security/headers.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_foundation_http.py`
- `scripts/runtime_latency_probe.py`

## Validacion local

- Foundation + marketplace tests: `25 passed, 1 warning`
- Full API pytest: `172 passed, 1 warning`
- Ruff: OK
- Compileall: OK
- Frontend build: OK

## Deploy staging

- Railway deployment: `16c94aa4-fdb5-4a93-80f2-6f95bdf27fd2`
- Service: `nodo-api`
- Replicas: `2/2`
- Health: OK

## Evidencia directa

### Single health request

`curl -i /api/v1/health` mostro:

- `x-nodo-process-time-ms: 0.6205`
- `server-timing: app;dur=0.6205`
- Railway edge: `mia1`

Esto prueba que el handler interno responde en menos de 1 ms para health.

### Local probe c100 contra health

Evidence: `evidence/slice_runs/slice18c_health_timing_c100_20260710170451.json`

- Requests: `600`
- Errors: `0`
- Client observed p50: `1046.614 ms`
- Client observed p95: `4927.7116 ms`
- Client observed p99: `7913.2164 ms`
- Server process p50: `0.643 ms`
- Server process p95: `4.0048 ms`
- Server process p99: `6.5593 ms`

Conclusion: la demora grande no ocurre dentro de FastAPI/NODO.

## Metricas Railway

### Health

Railway HTTP metrics, last 15m:

- Total: `1602`
- 5xx: `0`
- Error rate: `0.0`
- p50: `2 ms`
- p95: `44 ms`
- p99: `75 ms`

### Marketplace search

Railway HTTP metrics, last 30m:

- Total: `1000`
- 5xx: `0`
- Error rate: `0.0`
- p50: `5 ms`
- p95: `85 ms`
- p99: `138 ms`

### Ready

Railway HTTP metrics, last 30m:

- Total: `199`
- 5xx: `0`
- Error rate: `0.0`
- p50: `295 ms`
- p95: `637 ms`
- p99: `738 ms`

Ready toca DB/Redis, por eso es mas alto que health/marketplace. Aun asi no muestra la latencia extrema que ve el cliente local.

### CPU/memory

Railway metrics, last 15m:

- CPU average: `0.0205 vCPU`
- CPU max: `0.20902 vCPU`
- Memory current: `139.7458 MB`
- Memory limit: `1024 MB`
- Memory utilization: `13.6%`

## Diagnostico

El cuello observado desde la PC no esta en:

- handler FastAPI
- DB principal para marketplace
- Redis/cache para marketplace
- CPU
- memoria
- replicas Railway

Railway ve marketplace p95 `85 ms`, mientras la PC ve p95 de varios segundos bajo concurrencia local. Esto indica que la medicion local esta dominada por red/harness/conexion cliente a Railway, no por NODO.

## Decision tecnica

No seguir optimizando queries ni cache de marketplace hasta tener evidencia de cuello backend real.

A partir de este punto, las pruebas de capacidad deben separar:

1. `client_observed_latency`
2. `server_process_time`
3. `railway_http_total_duration`
4. `dependency_time`

Un p95 local alto no bloquea por si solo si Railway y `Server-Timing` muestran backend sano.

## Riesgo residual

- La experiencia real del usuario final todavia depende de su red, Telegram WebView, ubicacion y routing.
- Para validar experiencia real se necesita smoke desde dispositivo/region objetivo.
- Para validar capacidad se necesita runner cloud cercano o distribuido, no solo una PC local.

## Siguiente accion concreta

Construir/usar un runner cloud de capacidad para ejecutar desde infraestructura cercana a Railway/usuarios objetivo.

Mientras tanto, el criterio tecnico para backend debe basarse en:

- Railway HTTP metrics
- `X-NODO-Process-Time-Ms`
- errores 5xx
- invariantes
- DB/Redis metrics
- costo por request

No en p95 local aislado sin separar transporte.
