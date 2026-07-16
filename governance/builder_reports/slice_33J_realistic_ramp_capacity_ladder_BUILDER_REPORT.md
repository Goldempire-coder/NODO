# slice_33J_realistic_ramp_capacity_ladder - BUILDER REPORT

Estado final: INSUFFICIENT_EVIDENCE

## Scope ejecutado

- Run staging diagnostics only.
- Se agrego soporte de tooling para `traffic_shape=ramp|steady` en `scripts/marketplace_delivery_diagnostics.py`.
- Se preparo fixture sintetico staging con 250 businesses y 1500 ads activos.
- Se ejecuto solo c250 ramp60.
- No se ejecuto c500/c1000/c2500 porque c250 no paso estrictamente el contrato: el output quedo con `exit_code=1` por un `READ_TIMEOUT`/599 aislado.

## Archivos modificados

- `scripts/marketplace_delivery_diagnostics.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Evidencia creada

- `evidence/slice_runs/slice_33J_preflight.json`
- `evidence/slice_runs/slice_33J_fixture_apply.json`
- `evidence/slice_runs/slice_33J_delivery_c250_ramp60.json`
- `evidence/slice_runs/cleanup_slice_33J_delivery_c250_ramp60_before.json`
- `evidence/slice_runs/cleanup_slice_33J_delivery_c250_ramp60.json`
- `evidence/slice_runs/cleanup_slice_33J_delivery_c250_ramp60_after.json`
- `evidence/slice_runs/cleanup_slice_33J_fixture_before.json`
- `evidence/slice_runs/cleanup_slice_33J_fixture.json`
- `evidence/slice_runs/cleanup_slice_33J_fixture_after.json`
- `evidence/slice_runs/slice_33J_summary.json`
- `evidence/slice_runs/slice_33J_realistic_ramp_capacity_ladder_test_results.json`

## Fixture

| metric | value |
| --- | ---: |
| businesses inserted | 250 |
| ads inserted | 1500 |
| marketplace_visible_ads | 1500 |
| invalid_ads | 0 |
| duration_ms | 23540.718 |

## Capacity ladder

| level | status | reason |
| --- | --- | --- |
| c250 ramp60 | measured, not verified | 1999/2000 HTTP 200, 1 READ_TIMEOUT/599, exit_code=1 |
| c500 ramp120 | not run | c250 did not strictly pass |
| c1000 ramp180 | not run | c250 did not strictly pass |
| c2500 ramp300 | not run | c250 did not strictly pass |

## c250 metrics

| metric | value |
| --- | ---: |
| requested_requests | 2000 |
| actual_requests | 2000 |
| concurrency | 250 |
| traffic_shape | ramp |
| ramp_duration_seconds | 60 |
| status_counts | 1999x200, 1x599 |
| error_counts | 1 READ_TIMEOUT |
| error_rate | 0.0005 |
| throughput_rps | 4.1236 |
| client p95 ms | 324.4413 |
| client p99 ms | 509.8114 |
| backend p95 ms | 146.7606 |
| backend p99 ms | 184.7845 |
| external_gap p95 ms | 224.7175 |
| external_gap p99 ms | 423.8666 |
| TTFB p95 ms | 318.6654 |
| TTFB p99 ms | 504.7627 |
| response_read p95 ms | 12.678 |
| response KB p95 | 40.6504 |
| cache_hit_ratio | 0.977587 |
| DB acquire p95 ms | 0.0965 |
| DB query p95 ms | 141.4415 |
| cache lock wait p95 ms | 69.8962 |
| captured_profiles | 1499 |

Interpretacion: las metricas de latencia ramp son sanas y no apuntan a DB/cache/producto. Sin embargo, el contrato del slice exige `exit_code=0`; el unico `READ_TIMEOUT` ocurrio antes de recibir headers y fuerza detener la escalera.

## Tabla por flow step

| flow step | requests | status/errors | client p95 ms | backend p95 ms | TTFB p95 ms | response KB p95 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| marketplace_home | 500 | 500x200 / 0 | 340.3053 | 58.1502 | 323.3443 | 40.6523 |
| marketplace_filtered_search | 500 | 499x200, 1x599 / 1 READ_TIMEOUT | 244.0897 | 59.8435 | 237.7237 | 17.0449 |
| marketplace_ad_detail | 500 | 500x200 / 0 | 355.1387 | 179.9885 | 352.5096 | 1.1855 |
| marketplace_next_page | 500 | 500x200 / 0 | 204.5688 | 26.7733 | 198.9079 | 16.9912 |

## Operational cost units

- HTTP requests measured: 2000.
- Response total: 37798.1562 KB.
- Synthetic users used by diagnostics: 500.
- Fixture rows: 250 businesses, 1500 ads, 1500 credits ledger rows, 250 payment methods, 250 access links, 250 wallets.
- These are operational units, not dollar estimates.

## Cleanup

Diagnostics run cleanup:
- Before: 1000 sessions, 500 users retained by design.
- Apply: deleted 1000 sessions.
- After: 0 sessions; users retained by design.

Fixture cleanup:
- Before: 250 businesses, 1500 ads, 1500 ledger rows, 250 payment methods, 250 access links, 250 wallets.
- Apply: deleted all mutable fixture rows and nulled 1500 ads credit-ledger references before deleting ledger.
- After: businesses=0, ads=0, credits_ledger=0, business_payment_methods=0, business_access_links=0, credit_wallets=0, sessions=0. Users and audit logs retained by design.

## What was not tested

- Payments.
- Mass order creation.
- Admin.
- Support.
- Base RPC.
- Production.

## Recommendation

Do not tune marketplace, DB, cache, frontend, workers, pool, or infrastructure from this run. The next useful step is to remove the remaining diagnostic ambiguity before c500:

- rerun c250 ramp60 with a longer local command timeout and/or improved synthetic remitter/session setup;
- investigate the isolated `READ_TIMEOUT` transport path;
- only run c500 after c250 produces `exit_code=0`.

## Validations

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short` -> 108 passed.
- `python -m pytest apps/api/tests -q` -> 313 passed.
- `python -m ruff check apps/api scripts` -> passed.
- `python -m compileall apps/api apps/web/src scripts` -> passed.
- `corepack pnpm --filter @nodo/web build` -> passed.
- Slice 33J artifact value scan for sensitive values -> passed.

## Confirmations

- No product changes.
- No frontend product changes.
- No migrations.
- No infra changes.
- No deploy.
- No production.
- No READY_FOR_REAL_USE.
