# slice_33A7_connection_origin_and_route_confirmation BUILDER_REPORT

## Estado final

`BLOCKED_BY_GITHUB_ACTIONS_TOOLING`

El origen local/Codex fue medido contra staging con endpoints livianos. La comparación contra GitHub Actions no pudo ejecutarse desde esta sesión porque `gh` no está instalado/autenticado y no hay contexto de despacho/artifact disponible. Se dejó un workflow seguro para ejecutar el mismo probe desde GitHub Actions.

## Scope ejecutado

- No se modificó backend de producto.
- No se modificó frontend de producto.
- No se modificaron migraciones.
- No se cambió infraestructura.
- No se hizo deploy.
- No se tocó producción.
- No se usaron datos reales.
- No se declaró `READY_FOR_REAL_USE`.

## Archivos creados/modificados

- `scripts/connection_origin_probe.py`
- `.github/workflows/nodo-connection-origin-probe.yml`
- `apps/api/tests/test_staging_validation_tooling.py`
- `evidence/slice_runs/slice_33A7_local_origin_probe.json`
- `evidence/slice_runs/slice_33A7_github_actions_origin_probe.json`
- `evidence/slice_runs/slice_33A7_summary.json`
- `evidence/slice_runs/slice_33A7_connection_origin_and_route_confirmation_test_results.json`
- `governance/builder_reports/slice_33A7_connection_origin_and_route_confirmation_BUILDER_REPORT.md`

## Resultado local

Target público staging:

`https://nodo-api-production.up.railway.app`

Endpoints:

- `/api/v1/health`
- `/api/v1/ready`
- `/api/v1/version`

Matriz local c100:

| endpoint | status | client p95 ms | TTFB p95 ms | backend p95 ms | errores |
|---|---:|---:|---:|---:|---:|
| health | 298x200, 2x599 | 3725.24 | 3669.365 | 205.1245 | 2 CONNECT_ERROR |
| ready | 300x200 | 3369.9242 | 3366.9906 | 941.2708 | 0 |
| version | 300x200 | 4705.5956 | 4686.739 | 21.4972 | 0 |

Clasificación local:

- Principal: `LOCAL_ROUTE_LIMIT`
- Secundarias:
  - `CONNECTION_CHURN_LIMIT`
  - `CURL_DNS_CONNECT_TLS_HIGH`

## Curl phase probe local

| endpoint | clasificación | DNS p95 ms | TCP connect p95 ms | TLS p95 ms | server wait p95 ms | total p95 ms |
|---|---|---:|---:|---:|---:|---:|
| health | CURL_DNS_CONNECT_TLS_HIGH | 100.166 | 7207.248 | 118.808 | 222.135 | 7347.989 |
| ready | INCONCLUSIVE | 63.582 | 197.494 | 185.26 | 353.3 | 630.363 |
| version | CURL_DNS_CONNECT_TLS_HIGH | 106.131 | 7058.346 | 189.213 | 236.378 | 7354.371 |

Interpretación:

La ruta local también reproduce el síntoma de conexión TCP lenta contra endpoints livianos. Esto refuerza que no debe culparse DB, cache, marketplace, payload ni frontend. La comparación GitHub vs local sigue incompleta porque falta ejecutar el probe desde GitHub Actions.

## GitHub Actions

Se creó `.github/workflows/nodo-connection-origin-probe.yml`.

El workflow:

- usa `workflow_dispatch`;
- instala solo `httpx`;
- crea un env de guardrail no secreto;
- ejecuta `scripts/connection_origin_probe.py`;
- sube `slice_33A7_github_actions_origin_probe.json` como artifact.

No se pudo ejecutar desde esta sesión:

- `gh --version` falló porque `gh` no está disponible.
- No se imprimieron ni usaron secretos.

## Direct URL

Resultado: `DIRECT_URL_UNAVAILABLE`.

No existe `NODO_STAGING_DIRECT_API_BASE_URL` en el env local y no se inventó una URL directa Railway. La comparación public vs direct queda pendiente.

## Pool, keepalive y HTTP/2

- Pool classification: `INCONCLUSIVE`.
- Keepalive classification: `CONNECTION_CHURN_LIMIT`.
- HTTP/2: `HTTP2_PROBE_UNAVAILABLE`, falta paquete `h2`.

## Validaciones

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`: passed, 91 tests.
- `python -m pytest apps\api\tests -q`: passed, 296 tests.
- `python -m ruff check apps\api scripts`: passed.
- `python -m compileall apps\api apps\web\src scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- Scan de JSON `slice_33A7_*.json`: sin marcadores sensibles contractuales.

## Recomendación 33B

No optimizar producto.

Siguiente paso mínimo:

1. Ejecutar el nuevo workflow en GitHub Actions y descargar artifact.
2. Obtener o confirmar si existe una URL directa Railway segura para staging.
3. Comparar:
   - local vs GitHub Actions;
   - public URL vs direct URL si existe;
   - keepalive on/off;
   - c100 endpoints livianos.

Si GitHub y local son lentos, investigar Railway public route/edge/ingress antes de tocar DB/cache/backend. Si GitHub es lento y local no, cambiar método/origen del runner para pruebas de capacidad.
