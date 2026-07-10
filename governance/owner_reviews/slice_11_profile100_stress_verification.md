# slice_11 local stress profile 100 verification

Date: 2026-07-04

Status: PASSED_AFTER_FIXES

This is not READY_FOR_REAL_USE. This is the final local Postgres/Redis stress profile before connecting real managed services.

## Scope

- Local Docker Postgres: `nodo_postgres_local`
- Local Docker Redis: `nodo_redis_local`
- Stress profile: `100`
- Run id: `profile100_owner_run_poolfix_20260704214840`
- Evidence JSON: `evidence/slice_runs/slice_11_local_stress_profile100.json`
- Evidence log: `evidence/slice_runs/slice_11_local_stress_profile100.log`

## Profile target

- Businesses: `200`
- Orders: `2000`
- Marketplace searches: `2000`
- Stripe events: `200`
- Manual reviews: `200`

## Findings fixed during profile 100

1. The first attempt failed during business approvals with:

```txt
psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 55432 failed: Address already in use
```

2. Root cause: runtime repositories and audit writer opened too many short-lived Postgres TCP connections during high-volume local stress.

3. Fix applied:

- Added `apps/api/app/shared/db/connection.py`.
- Added `apps/api/app/shared/db/__init__.py`.
- Updated Postgres repositories and `PostgresAuditWriter` to use reusable per-thread connections via `pooled_connect`.
- Kept health check direct connection behavior unchanged.

## Final profile 100 result

- Exit code: `0`
- Steps recorded: `9006`
- Total requests: `8805`
- Total errors: `0`
- Total error rate: `0.0`
- Duration: `1150.178s`
- Throughput: `7.6553 req/s`
- p50: `92.4613 ms`
- p95: `168.9829 ms`
- p99: `268.4748 ms`

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

## Schema validation

Pre-stress schema validation:

- Evidence: `evidence/slice_runs/slice_11_profile100_schema_after_pool_fix.json`
- Tables: `23`
- Indexes: `128`
- Redis ping: `true`
- Failures: `[]`

Post-stress schema validation:

- Evidence: `evidence/slice_runs/slice_11_profile100_post_schema_validation.json`
- Tables: `23`
- Indexes: `128`
- Redis ping: `true`
- Failures: `[]`

## Verification after fixes

- `python scripts\run_slice_11_tests.py`: passed
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: `92 passed, 1 warning`
- `python -m ruff check apps\api scripts`: passed
- `python -m compileall apps scripts`: passed
- `corepack pnpm --filter @nodo/web build`: passed

## Recommendation

Local stress gates `25`, `50`, and `100` have passed after fixes. The next phase should be real managed service setup:

- Supabase Pro Postgres
- Railway backend
- Upstash Redis
- Cloudflare Pages frontend
- Cloudflare R2 or Supabase Storage
- Stripe test mode
- Telegram test mode

Do not declare READY_FOR_REAL_USE until smoke tests pass against real services.

