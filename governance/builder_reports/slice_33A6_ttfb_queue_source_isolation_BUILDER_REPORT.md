# BUILDER_REPORT - slice_33A6_ttfb_queue_source_isolation

## Estado final

TTFB_QUEUE_SOURCE_PARTIALLY_IDENTIFIED

La fuente fina queda parcialmente aislada: no es un problema marketplace-only ni DB/cache/backend. La evidencia apunta a ruta externa de entrega/conexion: health, ready, version y marketplace muestran TTFB alto bajo concurrencia, y el probe con curl ubica p95 alto en `tcp_connect_ms` para health/ready/marketplace search.

Clasificacion principal:

- `CURL_DNS_CONNECT_TLS_HIGH`

Clasificaciones secundarias:

- `HEALTH_READY_TTFB_QUEUE`
- `NETWORK_DELIVERY`
- `CONNECTION_REUSE_IMPORTANT`
- `HARNESS_TRANSPORT_ERRORS_PRESENT`

## Archivos creados/modificados

- `scripts/ttfb_queue_probe.py`
- `scripts/curl-format-ttfb.txt`
- `apps/api/tests/test_staging_validation_tooling.py`
- `evidence/slice_runs/slice_33A6_*.json`
- `evidence/slice_runs/cleanup_slice_33A6_*.json`
- `evidence/slice_runs/slice_33A6_summary.json`
- `evidence/slice_runs/slice_33A6_ttfb_queue_source_isolation_test_results.json`

No se modifico backend de producto, frontend, migraciones ni infraestructura.

## Endpoint isolation

| Endpoint | Status | Client p95 ms | Backend p95 ms | TTFB p95 ms | Read p95 ms | KB p95 | Clasificacion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| health | 299x200, 1x599 | 4531.8299 | 52.1417 | 4529.4100 | 75.9540 | 0.2041 | MIXED |
| ready | 300x200 | 2000.7663 | 1052.9204 | 1998.0616 | 6.3645 | 0.2002 | RUNTIME_QUEUE |
| version | 297x200, 3x599 | 7457.9435 | 84.5795 | 4194.8734 | 73.5817 | 0.2148 | MIXED |
| marketplace_home | 299x200, 1x599 | 4985.9414 | 303.2912 | 4956.8066 | 86.5471 | 39.7393 | MIXED |
| marketplace_filtered_search | 286x200, 14x599 | 15630.7021 | 257.7783 | 3579.9344 | 73.2030 | 16.0381 | MIXED |
| marketplace_ad_detail | 296x200, 4x599 | 4604.4683 | 607.2248 | 4388.7945 | 63.6028 | 1.1875 | MIXED |

Conclusion: health/ready/version tambien sufren TTFB alto. No corresponde culpar a marketplace search como ruta unica.

## Concurrency ramp

Knee detectado:

- health: primer TTFB p95 > 1000 ms en c50; primer client p95 > 3000 ms en c100.
- marketplace_home: primer TTFB p95 > 1000 ms en c50; primer client p95 > 3000 ms en c100; primer transport error en c50.

| Endpoint | c | Status | Client p95 ms | Backend p95 ms | TTFB p95 ms | Read p95 ms |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| health | 1 | 50x200 | 223.2125 | 4.0593 | 222.2066 | 1.4731 |
| health | 25 | 300x200 | 489.1367 | 36.0567 | 485.9773 | 10.0142 |
| health | 50 | 500x200 | 1495.6436 | 20.5357 | 1487.3197 | 15.5670 |
| health | 100 | 500x200 | 5333.8396 | 55.0486 | 5324.4847 | 79.3320 |
| marketplace_home | 1 | 50x200 | 215.0062 | 17.8565 | 213.6542 | 19.6888 |
| marketplace_home | 25 | 300x200 | 688.3251 | 97.7072 | 678.6420 | 22.3154 |
| marketplace_home | 50 | 498x200, 2x599 | 1611.7674 | 156.1481 | 1519.2687 | 34.1227 |
| marketplace_home | 100 | 499x200, 1x599 | 4907.1807 | 165.5397 | 4873.7048 | 121.2272 |

## Pool isolation

`HARNESS_POOL_LIMIT` no queda confirmado.

| Endpoint | max_connections | Status | Client p95 ms | Backend p95 ms | TTFB p95 ms |
| --- | ---: | --- | ---: | ---: | ---: |
| health | 10 | 500x200 | 3056.0386 | 12.0471 | 3050.3360 |
| health | 100 | 500x200 | 4437.0997 | 58.2445 | 4417.1887 |
| health | 200 | 499x200, 1x599 | 5062.9406 | 55.2506 | 5057.9585 |
| marketplace_home | 10 | 499x200, 1x599 | 3578.4311 | 28.1340 | 3556.8924 |
| marketplace_home | 100 | 500x200 | 7716.4717 | 134.1811 | 7685.5243 |
| marketplace_home | 200 | 499x200, 1x599 | 5847.1746 | 135.5819 | 5822.4151 |

## Keepalive isolation

`CONNECTION_REUSE_IMPORTANT` queda confirmado para health, pero no resuelve por si solo el problema.

| Endpoint | Keepalive | Status | Client p95 ms | Backend p95 ms | TTFB p95 ms |
| --- | --- | --- | ---: | ---: | ---: |
| health | on | 499x200, 1x599 | 4793.6609 | 52.7885 | 4783.3907 |
| health | off | 499x200, 1x599 | 7455.8424 | 48.9235 | 7454.6970 |
| marketplace_home | on | 498x200, 2x599 | 7742.7713 | 129.7371 | 7571.6145 |
| marketplace_home | off | 496x200, 4x599 | 7480.7869 | 315.3981 | 7444.8354 |

## HTTP/2

`HTTP2_PROBE_UNAVAILABLE`.

Motivo: `httpx.AsyncClient(http2=True)` requiere paquete `h2`, no instalado. No se instalaron dependencias.

## Curl phase probe

Curl ubico el p95 alto principalmente en conexion TCP, no en `server_wait_ms` ni descarga.

| Endpoint | Status | DNS p95 ms | TCP connect p95 ms | TLS p95 ms | Server wait p95 ms | Download p95 ms | Total p95 ms | Clasificacion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| health | 20x200 | 101.398 | 7063.066 | 193.613 | 193.263 | 14.483 | 7304.153 | CURL_DNS_CONNECT_TLS_HIGH |
| ready | 20x200 | 123.850 | 7139.738 | 187.516 | 368.830 | 11.039 | 7413.001 | CURL_DNS_CONNECT_TLS_HIGH |
| marketplace_home | 20x200 | 69.466 | 7130.406 | 223.604 | 248.254 | 184.641 | 7827.420 | CURL_DNS_CONNECT_TLS_HIGH |
| marketplace_ad_detail | 19x200, 1 curl_error | 160.875 | 307.468 | 765.356 | 321.820 | 3.920 | 1176.107 | INSUFFICIENT_EVIDENCE |

## Sequential stability

Secuencial c1 no reproduce el problema sostenido. Hubo un outlier inicial en health, pero p95 se mantiene bajo:

| Endpoint | Status | Client p95 ms | Backend p95 ms | TTFB p95 ms | Read p95 ms |
| --- | --- | ---: | ---: | ---: | ---: |
| health | 20x200 | 245.5776 | 3.5135 | 244.1265 | 1.7206 |
| ready | 20x200 | 396.3876 | 145.5242 | 395.4104 | 1.2066 |
| marketplace_home | 20x200 | 248.6302 | 14.8611 | 239.1932 | 9.4369 |
| marketplace_ad_detail | 20x200 | 293.6900 | 147.1425 | 292.4179 | 2.9476 |

## Fixture y cleanup

Fixture aplicado:

- users: 251
- businesses: 250
- business_access_links: 250
- business_payment_methods: 250
- credit_wallets: 250
- ads: 1500
- credits_ledger: 1500
- marketplace_visible_ads: 1500
- invalid_ads: 0

Cleanup:

- sesiones de runs diagnosticos: 0 despues de cleanup.
- businesses/ads/credits_ledger/business_access_links/business_payment_methods/credit_wallets del fixture: 0 despues de cleanup.
- users retenidos por diseno: si, por referencias append-only/audit.
- audit logs: retenidos por diseno.

## Que NO se debe arreglar todavia

- No optimizar DB/cache/marketplace por esta evidencia.
- No subir pool/workers/planes Railway/Supabase/Upstash.
- No cambiar lifecycles ni reglas de negocio.
- No tocar frontend/producto para este hallazgo.
- No declarar capacidad productiva con base en estas pruebas.

## Recomendacion 33B

Siguiente paso recomendado: investigar ruta runner/red/edge/plataforma, no producto marketplace.

Plan minimo:

1. Repetir curl phase probe desde otro origen controlado, idealmente GitHub Actions y/o otro runner cercano, con los mismos endpoints.
2. Comparar `tcp_connect_ms` por origen y por region/edge si Railway expone headers suficientes.
3. Si TCP connect alto solo aparece desde el runner local, clasificar como network/client route.
4. Si aparece desde varios origenes, escalar investigacion de edge/Railway/network sin cambiar aplicacion todavia.
5. Solo si `server_wait_ms` empieza a dominar con backend process bajo, investigar runtime/edge queue.

## Validaciones

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short`: 85 passed, 1 warning.
- `python -m pytest apps/api/tests -q`: 290 passed, 1 warning.
- `python -m ruff check apps/api scripts`: passed.
- `python -m compileall apps/api apps/web/src scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- Scan de evidencias 33A6: solo coincidencias benignas de `DATABASE_URL`/`REDIS_URL` con valor `[REDACTED]`; sin valores sensibles reales ni marcadores privados de producto.

## Confirmaciones

- No producto backend.
- No frontend.
- No migraciones.
- No infraestructura.
- No deploy.
- No produccion.
- No `READY_FOR_REAL_USE`.
