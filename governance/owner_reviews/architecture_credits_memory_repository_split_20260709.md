# Architecture Review - Credits Memory Repository Split

## Status

PASSED_AFTER_REFACTOR

## Scope

Phase 2 of credits repository cleanup: separated in-memory runtime implementation from Postgres repository file.

## Files changed

- `apps/api/app/modules/credits/memory_repository.py`
- `apps/api/app/modules/credits/repository.py`

## What changed

- Moved `InMemoryCreditRepository` into `memory_repository.py`.
- Kept `repository.py` as the compatibility import surface for `InMemoryCreditRepository` and `PostgresCreditRepository`.
- Preserved current imports in `app.main`.
- Kept all public method names, constructor signatures, in-memory state shape and behavior unchanged.
- Did not touch Postgres SQL, transactions, wallet updates, ledger writes, Stripe/manual payment rules or referral rules.

## Measurements

- `apps/api/app/modules/credits/repository.py`: 495 lines.
- `apps/api/app/modules/credits/memory_repository.py`: 298 lines.
- `apps/api/app/modules/credits/row_mappers.py`: 97 lines.
- Previous `credits/repository.py` size after row mapper split: 783 lines.

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

- `PostgresCreditRepository` remains in `repository.py`; it can be moved to `postgres_repository.py` in a later phase.
- `memory_repository.py` is still 298 lines but acceptable for a focused test/local implementation.
- No production readiness is implied.

## READY_FOR_REAL_USE

Not declared.
