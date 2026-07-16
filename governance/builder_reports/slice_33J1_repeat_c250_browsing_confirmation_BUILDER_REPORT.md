# slice_33J1_repeat_c250_browsing_confirmation - BUILDER REPORT

Estado final: C250_BROWSING_FAILED_TRANSPORT

Conclusion explicita: No comprobado.

## Scope ejecutado

- Staging only.
- Fixture sintetico rapido: 250 businesses, 6 ads por business, 1500 ads visibles.
- Marketplace browsing c250 ramp60.
- 2000 requests medidos.
- Keepalive on.
- Marketplace profile on.
- Cleanup obligatorio ejecutado para diagnostic run y fixture run.
- Sin producto, frontend, migraciones, infraestructura, deploy ni produccion.

## Evidencia creada

- `evidence/slice_runs/slice_33J1_preflight.json`
- `evidence/slice_runs/slice_33J1_fixture_apply.json`
- `evidence/slice_runs/slice_33J1_delivery_c250_ramp60.json`
- `evidence/slice_runs/cleanup_slice_33J1_delivery_c250_ramp60_before.json`
- `evidence/slice_runs/cleanup_slice_33J1_delivery_c250_ramp60.json`
- `evidence/slice_runs/cleanup_slice_33J1_delivery_c250_ramp60_after.json`
- `evidence/slice_runs/cleanup_slice_33J1_fixture_before.json`
- `evidence/slice_runs/cleanup_slice_33J1_fixture.json`
- `evidence/slice_runs/cleanup_slice_33J1_fixture_after.json`
- `evidence/slice_runs/slice_33J1_summary.json`
- `evidence/slice_runs/slice_33J1_repeat_c250_browsing_confirmation_test_results.json`

## Fixture

| metric | value |
| --- | ---: |
| businesses inserted | 250 |
| ads inserted | 1500 |
| marketplace_visible_ads | 1500 |
| invalid_ads | 0 |
| active_access_links | 250 |
| valid_wallets | 250 |
| duration_ms | 22624.946 |

## 33J vs 33J1

| metric | 33J c250 | 33J1 c250 |
| --- | ---: | ---: |
| requested_requests | 2000 | 2000 |
| actual_requests | 2000 | 2000 |
| synthetic_users_requested | 500 | 250 |
| synthetic_users_used | 500 | 500 |
| HTTP 200 | 1999 | 1995 |
| 599 / READ_TIMEOUT | 1 | 5 |
| transport error rate | 0.0005 | 0.0025 |
| client p95 ms | 324.4413 | 320.6631 |
| client p99 ms | 509.8114 | 420.0714 |
| backend p95 ms | 146.7606 | 149.8725 |
| backend p99 ms | 184.7845 | 187.6078 |
| TTFB p95 ms | 318.6654 | 316.1214 |
| TTFB p99 ms | 504.7627 | 408.3491 |
| external gap p95 ms | 224.7175 | 213.8319 |
| external gap p99 ms | 423.8666 | 350.1001 |
| DB acquire p95 ms | 0.0965 | 0.0464 |
| DB query p95 ms | 141.4415 | 110.8406 |
| cache hit ratio | 0.977587 | 0.972973 |
| response KB p95 | 40.6504 | 40.7002 |

## 33J1 flow steps

| flow step | requests | status/errors | client p95 ms | backend p95 ms | TTFB p95 ms | external gap p95 ms | response KB p95 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| marketplace_home | 500 | 500x200 / 0 | 278.0694 | 58.5708 | 274.3253 | 245.1912 | 40.7021 |
| marketplace_filtered_search | 500 | 495x200, 5x599 / 5 READ_TIMEOUT | 259.1822 | 58.4288 | 243.8752 | 208.3303 | 17.0469 |
| marketplace_ad_detail | 500 | 500x200 / 0 | 359.7352 | 184.6105 | 353.6629 | 203.0095 | 1.1875 |
| marketplace_next_page | 500 | 500x200 / 0 | 220.6548 | 48.0537 | 213.437 | 194.1004 | 17.0391 |

## Decision

`C250_BROWSING_FAILED_TRANSPORT`

Reasoning:

- `actual_requests == requested_requests`: yes.
- HTTP 200 rate: 99.75%, above 99.5%.
- 5xx application errors: 0.
- backend p95: 149.8725 ms, below 750 ms.
- TTFB p95: 316.1214 ms, below 1500 ms.
- client p95: 320.6631 ms, below 3000 ms.
- DB acquire/query and cache metrics do not dominate latency.
- Cleanup final: OK.
- But `READ_TIMEOUT` reproduced clearly: 5 timeouts in 33J1, all on `marketplace_filtered_search`, all before response headers.

This confirms the 33J timeout was not safely classifiable as one-off noise. The failure is transport/harness path behavior, not backend/product/DB/cache.

## Cleanup

Diagnostic run cleanup:

- Before: 500 users, 1000 sessions.
- Apply: deleted 1000 sessions.
- After: sessions=0; users retained by design.

Fixture cleanup:

- Before: 250 businesses, 1500 ads, 1500 credits ledger rows, 250 payment methods, 250 access links, 250 wallets.
- Apply: deleted all mutable fixture rows and nulled 1500 ads credit-ledger references before deleting ledger.
- After: businesses=0, ads=0, credits_ledger=0, business_payment_methods=0, business_access_links=0, credit_wallets=0, sessions=0. Users and audit logs retained by design.

## Not included

- Chat.
- Image uploads.
- Orders/transactions.
- Payments.
- Admin.
- Business Mini App.

## Recommendation

Do not optimize marketplace, DB, cache, frontend, pool, workers, plans or infrastructure from this result.

Next useful diagnostic:

- isolate why `marketplace_filtered_search` produces repeated client-side `READ_TIMEOUT` before headers while the same endpoint/route mostly returns with healthy p95;
- run a narrower c250/c100 probe focused only on filtered search with per-request timeout/arrival timing and possibly a second origin;
- keep c250 product browsing unverified until this transport timeout is explained or eliminated.

## Validation

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short` -> 108 passed.
- Slice 33J1 artifact value scan -> passed.

## Confirmations

- No product.
- No frontend.
- No migrations.
- No infrastructure.
- No deploy.
- No production.
- No real-use readiness declared.
