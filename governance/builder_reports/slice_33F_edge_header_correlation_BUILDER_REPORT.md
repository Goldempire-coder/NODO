# slice_33F_edge_header_correlation - BUILDER REPORT

Estado final: EDGE_CORRELATION_SOURCE_IDENTIFIED

## Scope ejecutado

- Tooling-only: `scripts/edge_header_correlation_probe.py`.
- Staging diagnostics sobre endpoints livianos:
  - `/api/v1/health`
  - `/api/v1/ready`
  - `/api/v1/version`
- No se usaron fixtures marketplace.
- No se tocaron backend de producto, frontend, migraciones, deploy ni infraestructura.

## Archivos modificados

- `scripts/edge_header_correlation_probe.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Evidencia creada

- `evidence/slice_runs/slice_33F_edge_header_correlation_sequential.json`
- `evidence/slice_runs/slice_33F_edge_header_correlation_c50.json`
- `evidence/slice_runs/slice_33F_edge_header_correlation_c100.json`
- `evidence/slice_runs/slice_33F_edge_header_correlation_summary.json`
- `evidence/slice_runs/slice_33F_edge_header_correlation_test_results.json`

## Resultado principal

Clasificación principal: `BEFORE_RAILWAY_EDGE_LIKELY`

Clasificación secundaria: `CLOCK_SKEW_LIMITED`

Interpretación:
- `X-Railway-Edge` y `X-Railway-Request-Id` aparecen en respuestas exitosas.
- El edge observado fue `mia1` en las respuestas exitosas.
- `X-NODO-Process-Time-Ms` se mantuvo bajo frente al tiempo de cliente.
- `X-Request-Start` no apareció en las respuestas observadas, por lo que no hay correlación confiable de reloj local vs edge.
- Las fases curl muestran que el tiempo dominante en varias muestras está en DNS/TCP/TLS antes de `starttransfer`, no en descarga ni app runtime.

## Tabla por corrida

| mode | endpoint | status | errors | client p95 ms | TTFB p95 ms | backend p95 ms | external gap p95 ms | read p95 ms | edge |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| sequential | health | 20x200 | 0 | 301.155 | 299.8479 | 3.0955 | 298.0595 | 1.3063 | mia1 |
| sequential | ready | 20x200 | 0 | 278.7972 | 277.3882 | 142.0914 | 151.1632 | 1.4078 | mia1 |
| sequential | version | 20x200 | 0 | 226.823 | 225.9119 | 2.798 | 224.8375 | 1.281 | mia1 |
| c50 | health | 200x200 | 0 | 7616.1504 | 7612.8232 | 9.871 | 7611.4912 | 16.6001 | mia1 |
| c50 | ready | 200x200 | 0 | 7488.1377 | 7487.2431 | 349.9795 | 7365.447 | 3.8587 | mia1 |
| c50 | version | 200x200 | 0 | 1350.1026 | 1341.5739 | 27.9946 | 1343.8027 | 16.843 | mia1 |
| c100 | health | 299x200, 1x599 | 1 CONNECT_ERROR | 4187.4805 | 4170.6956 | 43.1385 | 4182.4261 | 74.0173 | mia1, unknown |
| c100 | ready | 300x200 | 0 | 3579.6274 | 3575.9557 | 717.9554 | 3456.9454 | 44.5041 | mia1 |
| c100 | version | 300x200 | 0 | 3907.6931 | 3893.534 | 54.4991 | 3904.4672 | 81.7149 | mia1 |

## Curl phase summary

| mode | endpoint | dns p95 ms | tcp connect p95 ms | tls p95 ms | server wait p95 ms | download p95 ms | classification |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| sequential | health | 60.683 | 7117.041 | 133.724 | 196.808 | 10.998 | BEFORE_RAILWAY_EDGE_LIKELY |
| sequential | ready | 115.937 | 7132.21 | 165.505 | 307.736 | 0.077 | BEFORE_RAILWAY_EDGE_LIKELY |
| sequential | version | 125.837 | 7185.256 | 181.77 | 202.404 | 5.934 | BEFORE_RAILWAY_EDGE_LIKELY |
| c50 | health | 146.467 | 15081.545 | 146.114 | 225.09 | 13.206 | BEFORE_RAILWAY_EDGE_LIKELY |
| c50 | ready | 172.508 | 7184.446 | 116.219 | 344.34 | 0.263 | BEFORE_RAILWAY_EDGE_LIKELY |
| c50 | version | 18.152 | 181.013 | 194.786 | 221.256 | 14.262 | INSUFFICIENT_EVIDENCE |
| c100 | health | 50.436 | 575.619 | 117.228 | 184.088 | 10.073 | INSUFFICIENT_EVIDENCE |
| c100 | ready | 217.534 | 7158.2 | 190.452 | 349.219 | 5.495 | BEFORE_RAILWAY_EDGE_LIKELY |
| c100 | version | 35.172 | 7071.241 | 167.504 | 235.581 | 0.145 | BEFORE_RAILWAY_EDGE_LIKELY |

## Limitaciones

- `X-Request-Start` no fue devuelto por Railway en estas respuestas, por eso la correlación de reloj edge/local queda como `CLOCK_SKEW_LIMITED`.
- La evidencia no confirma un límite vendor específico.
- La evidencia no justifica cambios de DB, cache, marketplace, frontend, pool, workers ni planes.

## Recomendación

Siguiente investigación recomendada: `33H connection pattern` o `33I burst spacing`.

Razón:
- La app responde rápido cuando la request llega al backend.
- El cuello observado está antes de que la app pueda medirlo.
- El edge observado es dominante (`mia1`), pero falta correlación provider-side con logs Railway para cerrar edge vs ruta local.

## Validaciones

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short` -> 98 passed.
- `python -m pytest apps/api/tests -q` -> 303 passed.
- `python -m ruff check apps/api scripts` -> passed.
- `python -m compileall apps/api apps/web/src scripts` -> passed.
- `corepack pnpm --filter @nodo/web build` -> passed.
- Scan de artefactos 33F por secretos/tokens/storage/account/private keys -> passed.

## Confirmaciones

- No producto.
- No frontend.
- No migraciones.
- No infraestructura.
- No deploy.
- No producción.
- No READY_FOR_REAL_USE.
