# slice_11 local stress profile 25 verification

Date: 2026-07-04

Status: PASSED_AFTER_FIXES

This is not READY_FOR_REAL_USE. This is a local Postgres/Redis stress verification before Supabase/Redis cloud/storage/Telegram/deploy.

## Scope

- Local Docker Postgres: `nodo_postgres_local`
- Local Docker Redis: `nodo_redis_local`
- Stress profile: `25`
- Run id: `profile25_owner_run_nplus1fix_20260704204256`
- Evidence JSON: `evidence/slice_runs/slice_11_local_stress_profile25.json`
- Evidence log: `evidence/slice_runs/slice_11_local_stress_profile25.log`

## Findings fixed during profile 25

1. Stress seed reused a previous `run-id`, causing idempotency replay to return an old business owned by another user. This correctly produced `FORBIDDEN` during document upload. Resolution: rerun with clean DB and unique `run-id`.

2. Stress seed underfunded business wallets for profile 25 ad tiers. The product correctly returned `CREDIT_BALANCE_INSUFFICIENT`. Resolution: `scripts/stress_local.py` now calculates required credits per business from ad max amount tiers before publishing ads.

3. Marketplace search opened too many Postgres connections due to per-result business lookups. On Windows this reached `Address already in use` during profile 25. Resolution: ad search now batch-loads businesses with `get_businesses_by_ids` and reuses the map for payloads/ranking.

## Final profile 25 result

- Exit code: `0`
- Steps recorded: `2204`
- Total requests: `2153`
- Total errors: `0`
- Total error rate: `0.0`
- Duration: `530.877s`
- Throughput: `4.0556 req/s`
- p50: `190.2578 ms`
- p95: `399.5509 ms`
- p99: `637.098 ms`

## Invariant violations

All invariant counters were `0`:

- idempotency duplicates
- idempotency replay conflicts
- double credit consumption
- double credit accreditation
- negative balances
- invalid transitions
- Redis failures
- DB errors
- timeouts
- deadlocks
- job lock failures

## Post-stress schema validation

Result: passed.

- Tables: `23`
- Indexes: `128`
- Redis ping: `true`
- Failures: `[]`

Evidence: `evidence/slice_runs/slice_11_profile25_post_schema_validation.json`

## Verification after fixes

- `python -m ruff check apps\api scripts`: passed
- `python -m compileall apps scripts`: passed
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: `92 passed, 1 warning`
- `python scripts\run_slice_11_tests.py`: passed

## Recommendation

Proceed to local stress profile 50 only after owner accepts this profile 25 result.

