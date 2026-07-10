# Architecture Review - Credits Postgres Repository Split

## Status

PASSED_AFTER_REFACTOR

## Scope

Phase 3 of credits repository cleanup: separated Postgres runtime implementation from compatibility repository module.

## Files changed

- `apps/api/app/modules/credits/postgres_repository.py`
- `apps/api/app/modules/credits/repository.py`
- `apps/api/tests/test_credits_referrals.py`

## What changed

- Moved `PostgresCreditRepository` into `postgres_repository.py`.
- Left `repository.py` as a compatibility facade exporting `InMemoryCreditRepository` and `PostgresCreditRepository`.
- Updated the static contract test to inspect `postgres_repository.py` for Postgres SQL.
- Kept `app.main` imports unchanged.
- Kept SQL, transactions, wallet updates, ledger writes, Stripe/manual payment rules and referral rules unchanged.

## Measurements

- `apps/api/app/modules/credits/repository.py`: 7 lines.
- `apps/api/app/modules/credits/postgres_repository.py`: 491 lines.
- `apps/api/app/modules/credits/memory_repository.py`: 298 lines.
- `apps/api/app/modules/credits/row_mappers.py`: 97 lines.

## Validation

- `python -m pytest apps\api\tests\test_credits_referrals.py -q`
  - Result: 7 passed, 1 warning.
- `python -m pytest apps\api\tests -q`
  - Result: 133 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Result: passed.
- `python -m compileall apps\api scripts`
  - Result: passed.
- `corepack pnpm --filter @nodo/web build`
  - Result: passed.

## Residual risk

- `postgres_repository.py` is still 491 lines. This is acceptable for now because it contains the Postgres implementation and transaction-heavy SQL.
- Future cuts should target smaller helper extraction inside Postgres only after adding focused DB/concurrency tests for credit purchase approval.
- No production readiness is implied.

## READY_FOR_REAL_USE

Not declared.
