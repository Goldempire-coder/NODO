# slice_33I_burst_spacing_and_arrival_rate_policy - BUILDER REPORT

Estado final: ARRIVAL_RATE_SOURCE_IDENTIFIED

## Scope ejecutado

- Tooling-only: `scripts/burst_spacing_probe.py`.
- Staging diagnostics sobre endpoints livianos:
  - `/api/v1/version`
  - `/api/v1/health`
  - `/api/v1/ready`
- Sin fixtures marketplace.
- Sin cambios de producto, frontend, migraciones, deploy ni infraestructura.

## Archivos modificados

- `scripts/burst_spacing_probe.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Evidencia creada

- `evidence/slice_runs/slice_33I_burst_spacing_probe.json`
- `evidence/slice_runs/slice_33I_summary.json`
- `evidence/slice_runs/slice_33I_burst_spacing_and_arrival_rate_policy_test_results.json`

## Clasificación

Principal: `ARRIVAL_RATE_MITIGATES`

Secundarias:
- `BURST_CONNECTION_CHURN_CONFIRMED`
- `KEEPALIVE_REQUIRED`

Conclusión: c100 no falla por incapacidad sostenida de la app/backend. El problema aparece cuando el tráfico llega como burst instantáneo. Al espaciar llegadas o usar ramp/steady, el TTFB p95 baja de segundos a cientos de ms con backend p95 bajo.

## Tabla por traffic shape

| label | status/errors | client p95 ms | TTFB p95 ms | backend p95 ms | read p95 ms | duration s | edge |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| version_c100_burst_0ms | 300x200 / 0 | 7665.9884 | 7664.1512 | 43.6232 | 54.6578 | 15.9801 | mia1 |
| version_c100_spacing_10ms | 300x200 / 0 | 2584.6446 | 2566.0278 | 16.7338 | 36.101 | 16.5718 | mia1 |
| version_c100_spacing_50ms | 300x200 / 0 | 367.2136 | 366.2372 | 4.4873 | 2.8855 | 15.1963 | mia1 |
| version_c100_spacing_100ms | 300x200 / 0 | 232.9916 | 232.2166 | 5.8502 | 1.8612 | 30.0622 | mia1 |
| version_c100_ramp_30s | 300x200 / 0 | 238.48 | 237.6088 | 6.6649 | 1.8521 | 30.0957 | mia1 |
| version_c100_ramp_60s | 300x200 / 0 | 244.0781 | 243.1771 | 4.0479 | 1.4498 | 65.6931 | mia1 |
| version_c100_steady_5rps | 100x200 / 0 | 446.1573 | 445.1797 | 4.0754 | 1.4514 | 19.967 | mia1 |
| version_c100_steady_10rps | 100x200 / 0 | 493.7474 | 492.7644 | 5.6688 | 2.499 | 9.9952 | mia1 |
| version_c100_steady_20rps | 200x200 / 0 | 448.1613 | 447.044 | 9.3557 | 2.2569 | 10.1224 | mia1 |
| health_c100_burst_0ms | 299x200, 1x599 / 1 CONNECT_ERROR | 3730.8153 | 3718.3849 | 67.094 | 75.3026 | 21.683 | mia1, unknown |
| health_c100_spacing_50ms | 300x200 / 0 | 449.1925 | 448.4299 | 7.6295 | 2.91 | 16.9862 | mia1 |
| health_c100_ramp_60s | 300x200 / 0 | 267.4406 | 266.2498 | 3.9498 | 1.4857 | 60.1362 | mia1 |
| ready_c100_burst_0ms | 299x200, 1x599 / 1 CONNECT_ERROR | 1712.6486 | 1710.2897 | 1030.4856 | 9.5171 | 21.5479 | mia1, unknown |
| ready_c100_spacing_50ms | 300x200 / 0 | 424.14 | 423.4302 | 142.5212 | 2.6564 | 16.1715 | mia1 |
| ready_c100_ramp_60s | 300x200 / 0 | 496.1131 | 495.2932 | 145.8855 | 2.0305 | 60.226 | mia1 |

## c50 vs c100

| run | status/errors | TTFB p95 ms | backend p95 ms |
| --- | --- | ---: | ---: |
| version_c50_burst_0ms | 200x200 / 0 | 1378.2537 | 14.8588 |
| version_c50_ramp_30s | 200x200 / 0 | 221.3676 | 4.0742 |
| version_c100_burst_0ms | 300x200 / 0 | 7664.1512 | 43.6232 |
| version_c100_ramp_30s | 300x200 / 0 | 237.6088 | 6.6649 |

## Keepalive result

| run | TTFB p95 ms | backend p95 ms |
| --- | ---: | ---: |
| version_c100_burst_0ms keepalive on | 7664.1512 | 43.6232 |
| version_c100_burst_0ms keepalive off | 7531.2563 | 45.6948 |
| version_c100_ramp_60s keepalive on | 243.1771 | 4.0479 |
| version_c100_ramp_60s keepalive off | 7371.0031 | 3.5998 |

Interpretación: keepalive no corrige el burst instantáneo por sí solo, pero es obligatorio para que ramp/steady representen tráfico realista. Sin keepalive, incluso ramp 60s vuelve a TTFB p95 de ~7.37s.

## Edge distribution

- Respuestas exitosas: `mia1`.
- Errores de transporte aislados: `unknown` porque no hubo headers.

## Política recomendada

- Product gate staging:
  - máximo c50.
  - usar `ramp` o `steady`, no burst instantáneo.
  - keepalive on requerido.
- c100+:
  - solo `infra-probe`.
  - burst reservado para stress de edge/transporte, no para bloquear producto.
- No culpar DB/cache/marketplace/frontend mientras backend p95 siga bajo y el cuello sea TTFB/connect.

## Qué NO arreglar todavía

- No optimizar marketplace.
- No cambiar queries DB.
- No agregar cache.
- No subir pool/workers/planes.
- No cambiar frontend.
- No cambiar infraestructura.

## Validaciones

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short` -> 105 passed.
- `python -m pytest apps/api/tests -q` -> 310 passed.
- `python -m ruff check apps/api scripts` -> passed.
- `python -m compileall apps/api apps/web/src scripts` -> passed.
- `corepack pnpm --filter @nodo/web build` -> passed.
- Scan de artefactos 33I por datos sensibles -> passed.

## Confirmaciones

- No producto.
- No frontend.
- No migraciones.
- No infraestructura.
- No deploy.
- No producción.
- No READY_FOR_REAL_USE.
