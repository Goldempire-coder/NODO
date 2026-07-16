# slice_33A5_delivery_harness_target_and_phase_timing_BUILDER_REPORT

## Estado final

DELIVERY_PHASE_SOURCE_PARTIALLY_IDENTIFIED

## Cambios de tooling

- `scripts/marketplace_delivery_diagnostics.py`
  - `--requests N` ahora exige N requests medidos.
  - Autoexpande usuarios sinteticos: `steps_per_user=4`, `synthetic_users_used=ceil(requests/4)` cuando hace falta.
  - Si `actual_requests != requested_requests`, marca `REQUEST_TARGET_MISMATCH` y `exit_code=1`.
  - Agrega `--cache-mode cold|warm`.
  - Warm ejecuta prewarm separado y no lo cuenta como requests medidos.
  - Agrega timing por fases: `ttfb_or_headers_ms`, `response_read_ms`, monotonic start/end.
  - Clasifica globalmente el cuello probable.
- `apps/api/tests/test_staging_validation_tooling.py`
  - Tests de consumo exacto de requests, modos cold/warm, phase timing y clasificacion.

## Evidencia staging

- Preflight: `evidence/slice_runs/slice_33A5_preflight.json`
- Fixture apply: `evidence/slice_runs/slice_33A5_fixture_apply.json`
- Cold c100: `evidence/slice_runs/slice_33A5_delivery_c100_cold.json`
- Warm c100: `evidence/slice_runs/slice_33A5_delivery_c100_warm.json`
- Summary: `evidence/slice_runs/slice_33A5_delivery_summary.json`

## Resultados principales

| mode | requested | actual | status | errors | client p95 | backend p95 | gap p95 | ttfb p95 | read p95 | KB p95 | classification |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| cold | 1000 | 1000 | {'200': 1000} | {} | 5484.873 | 203.4653 | 5327.7469 | 5421.521 | 76.8794 | 40.582 | TTFB_EDGE_OR_RUNTIME_QUEUE |
| warm | 1000 | 1000 | {'200': 999, '599': 1} | {'READ_TIMEOUT': 1} | 5178.2942 | 167.0319 | 5157.3405 | 5165.4667 | 86.1119 | 40.582 | MIXED |

## Clasificacion

Principal: `TTFB_EDGE_OR_RUNTIME_QUEUE`.

Secundaria: `NETWORK_DELIVERY` / `HARNESS_TRANSPORT_ERRORS_PRESENT`.

Motivo: en cold y warm el p95 de backend queda bajo frente al p95 externo; `ttfb_or_headers` acompana casi todo el gap, mientras `response_read` queda bajo y payload p95 ronda 40.6 KB. No hay evidencia para culpar DB/cache/producto. Warm no queda como identificado limpio porque tuvo 1 `READ_TIMEOUT` medido y 1 timeout de prewarm.

## Cleanup

Cleanup ejecutado para:

- `slice33a5_delivery_c100_cold_20260712121340`
- `slice33a5_delivery_c100_warm_20260712122058`
- `slice33a5_delivery_c100_warm_20260712122850`
- `slice33a5_delivery_c100_warm_20260712123704`
- `slice33a5_fixture_20260712121301`

Despues del cleanup: businesses/ads/credits_ledger/business_payment_methods/business_access_links/credit_wallets/sessions quedaron en 0 para recursos mutantes. Users quedan retenidos por diseno cuando audit append-only los referencia.

## Validaciones

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short`: 77 passed, 1 warning
- `python -m pytest apps/api/tests -q`: 282 passed, 1 warning
- `python -m ruff check apps/api scripts`: All checks passed
- `python -m compileall apps/api apps/web/src scripts`: passed
- `corepack pnpm --filter @nodo/web build`: passed


## Scan de secretos

Resultado: passed_with_benign_matches.

- `DATABASE_URL` y `REDIS_URL` aparecen solo como `[REDACTED]` en payloads de guardrails/cleanup.
- `auth:marketplace_decode_access_token` aparece como nombre de stage de profiling, no como valor de token.
- No se encontraron valores reales de secretos, `storage_path`, `account_value`, private keys, seed phrases ni mnemonics en artefactos 33A5.

## Riesgos residuales

- La fase `ttfb_or_headers` no separa pool/connect/TLS porque httpx publico no lo expone sin instrumentacion de transporte mas baja.
- Warm presento transporte inestable: prewarm `READ_TIMEOUT` y corrida medida con 1 `READ_TIMEOUT`.
- El build staging observado fue `staging-28d-rollback-20260711210924`; no se cambio ni desplego nada en este slice.

## Confirmaciones

- No producto.
- No frontend.
- No migraciones.
- No infraestructura.
- No deploy.
- No produccion.
- No READY_FOR_REAL_USE.
