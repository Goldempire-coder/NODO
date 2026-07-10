# Architecture Review - Credits Row Mappers Split

## Status

PASSED_AFTER_REFACTOR

## Scope

Phase 1 of credits repository cleanup: extracted Postgres row mapping from `credits/repository.py`.

## Files changed

- `apps/api/app/modules/credits/row_mappers.py`
- `apps/api/app/modules/credits/repository.py`

## What changed

- Moved credit purchase row mapping to `row_mappers.py`.
- Moved credit wallet row mapping to `row_mappers.py`.
- Moved credit ledger row mapping to `row_mappers.py`.
- Moved file asset row mapping to `row_mappers.py`.
- Kept repository public API, class names, imports from `main.py`, transactions, SQL, locks, wallet changes, ledger writes and behavior unchanged.

## Measurements

- `apps/api/app/modules/credits/repository.py`: 783 lines.
- `apps/api/app/modules/credits/row_mappers.py`: 97 lines.
- Previous `credits/repository.py` size after prior cut: 873 lines.

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

- This is not the full runtime split yet. `InMemoryCreditRepository` and `PostgresCreditRepository` still live in the same file.
- Next safe phase: move `InMemoryCreditRepository` to `memory_repository.py` while keeping `repository.py` as a compatibility re-export.

## READY_FOR_REAL_USE

Not declared.
