# slice_33K_filtered_search_timeout_and_flow_burst_isolation - BUILDER REPORT

Estado final: BURST_SHAPE_CONFIRMED

Conclusion explicita: Comprobado hasta 250 usuarios concurrentes navegando marketplace con per-step cap c100. Sin ese cap, c250 browsing sigue no comprobado por READ_TIMEOUT repetidos.

## Scope ejecutado

- Tooling-only en `scripts/marketplace_delivery_diagnostics.py`.
- Instrumentacion por request:
  - `queue_wait_ms`
  - `step_number`
  - `request_ready_at`
  - `request_started_at`
  - `response_started`
  - `response_finished`
  - `exception_class`
  - `retry_attempt`
  - `recovered_by_retry`
- Resumen por step:
  - raw/recovered/unrecovered transport errors
  - queue wait p50/p95/p99
  - client/backend/TTFB
  - profile/cache/DB metrics
- Experimento ejecutado: 33K-E per-step concurrency cap c100.
- No se ejecuto retry.
- No se ejecutaron 33K-C/F/D/A-B porque 33K-E elimino los timeouts y fue concluyente.

## Archivos modificados

- `scripts/marketplace_delivery_diagnostics.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Evidencia creada

- `evidence/slice_runs/slice_33K_fixture_apply.json`
- `evidence/slice_runs/slice_33K_E_stepcap_c250_ramp60.json`
- `evidence/slice_runs/cleanup_slice_33K_E_stepcap_before.json`
- `evidence/slice_runs/cleanup_slice_33K_E_stepcap.json`
- `evidence/slice_runs/cleanup_slice_33K_E_stepcap_after.json`
- `evidence/slice_runs/cleanup_slice_33K_fixture_before.json`
- `evidence/slice_runs/cleanup_slice_33K_fixture.json`
- `evidence/slice_runs/cleanup_slice_33K_fixture_after.json`
- `evidence/slice_runs/slice_33K_summary.json`
- `evidence/slice_runs/slice_33K_filtered_search_timeout_and_flow_burst_isolation_test_results.json`

## Fixture

| metric | value |
| --- | ---: |
| businesses inserted | 250 |
| ads inserted | 1500 |
| marketplace_visible_ads | 1500 |
| invalid_ads | 0 |
| active_access_links | 250 |
| valid_wallets | 250 |
| duration_ms | 20761.325 |

## Comparative table

| run | shape / control | status | raw transport errors | filtered_search errors | client p95 ms | backend p95 ms | TTFB p95 ms | queue wait p95 ms | DB query p95 ms | cache hit ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 33J baseline | ramp60 | 1999x200, 1x599 | 1 | 1 | 324.4413 | 146.7606 | 318.6654 | n/a | 141.4415 | 0.977587 |
| 33J1 repeat | ramp60 | 1995x200, 5x599 | 5 | 5 | 320.6631 | 149.8725 | 316.1214 | n/a | 110.8406 | 0.972973 |
| 33K-E | ramp60 + per-step cap c100 | 2000x200 | 0 | 0 | 294.7483 | 147.0889 | 290.7363 | 0.0143 | 164.7461 | 0.974359 |

## 33K-E flow steps

| flow step | requests | status/errors | queue wait p95 ms | client p95 ms | backend p95 ms | TTFB p95 ms | response KB p95 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| marketplace_home | 500 | 500x200 / 0 | 0.0133 | 240.723 | 57.779 | 225.2888 | 40.6533 |
| marketplace_filtered_search | 500 | 500x200 / 0 | 0.0141 | 242.1571 | 57.3604 | 237.5947 | 17.001 |
| marketplace_ad_detail | 500 | 500x200 / 0 | 0.0146 | 342.2538 | 174.0762 | 340.8128 | 1.1865 |
| marketplace_next_page | 500 | 500x200 / 0 | 0.015 | 196.8015 | 25.9789 | 189.5991 | 16.9912 |

## Decision

`BURST_SHAPE_CONFIRMED`

Reasoning:

- Baselines 33J/33J1 failed with READ_TIMEOUT concentrated in `marketplace_filtered_search`.
- 33K-E kept the same c250, 2000 requests, ramp60, keepalive on, profile on, 250/1500 fixture.
- Only change in the experiment was per-step concurrency cap c100.
- 33K-E produced 2000/2000 HTTP 200.
- Raw transport errors: 0.
- Unrecovered transport errors: 0.
- Queue wait p95 stayed near zero, so the cap did not create an obvious harness queue bottleneck.
- Backend/DB/cache stayed healthy.

This points to flow step burst shape, not product, DB, cache, frontend or general endpoint reliability.

## Experiments not run

- 33K-C jitter: not run because 33K-E eliminated the timeout.
- 33K-F pool isolation: not run because 33K-E eliminated the timeout.
- 33K-D filtered_search only: not run because 33K-E eliminated the timeout.
- 33K-A/B ramp comparison: not run because 33K-E eliminated the timeout.
- Retry test: not run because no retry was needed to clean the run.

## Cleanup

Diagnostic 33K-E cleanup:

- Before: 500 users, 1000 sessions.
- Apply: deleted 1000 sessions.
- After: sessions=0; users retained by design.

Fixture cleanup:

- Before: 250 businesses, 1500 ads, 1500 credits ledger rows, 250 payment methods, 250 access links, 250 wallets.
- Apply: deleted all mutable fixture rows and nulled 1500 ads credit-ledger references before deleting ledger.
- After: businesses=0, ads=0, credits_ledger=0, business_payment_methods=0, business_access_links=0, credit_wallets=0, sessions=0. Users and audit logs retained by design.

## Next step

Use per-step concurrency shaping as staging harness policy for marketplace browsing. Then proceed to Business Mini App walkthrough under the shaped c250 policy.

Do not optimize marketplace route, DB, cache, frontend, workers, pool, plans or infrastructure from this evidence.

## Validation

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short` -> 112 passed.
- `python -m pytest apps/api/tests -q` -> 317 passed.
- `python -m ruff check apps/api scripts` -> passed.
- `python -m compileall apps/api apps/web/src scripts` -> passed.
- `corepack pnpm --filter @nodo/web build` -> passed.
- Slice 33K artifact value scan -> passed.

## Confirmations

- No product.
- No productive frontend.
- No migrations.
- No infrastructure.
- No deploy.
- No production.
- No real-use readiness declared.
