# Architecture Review - Orders Row Mappers Split

## Status

PASSED_AFTER_REFACTOR

## Scope

Phase 1 of orders repository cleanup: extracted Postgres row mapping from `orders/repository.py`.

## Files changed

- `apps/api/app/modules/orders/row_mappers.py`
- `apps/api/app/modules/orders/repository.py`

## What changed

- Moved order row mapping to `row_mappers.py`.
- Moved payment report row mapping to `row_mappers.py`.
- Moved file asset row mapping to `row_mappers.py`.
- Kept repository public API, class names, transactions, SQL, locks, order writes, payment report writes and behavior unchanged.

## Measurements

- `apps/api/app/modules/orders/repository.py`: 752 lines.
- `apps/api/app/modules/orders/row_mappers.py`: 91 lines.
- Previous `orders/repository.py` size: 837 lines.

## Validation

- `python -m pytest apps\api\tests\test_order_creation.py apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_jobs_notifications.py -q`
  - Result: 30 passed, 1 warning.
- `python -m pytest apps\api\tests -q`
  - Result: 133 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Result: passed.
- `python -m compileall apps\api scripts`
  - Result: passed.
- `corepack pnpm --filter @nodo/web build`
  - Result: passed.

## Residual risk

- `orders/repository.py` still contains both in-memory and Postgres implementations.
- Next safe phase: split `InMemoryOrderRepository` into `memory_repository.py`, keeping `repository.py` as compatibility facade.
- `confirm_business_payment_with_credit_consumption` remains the longest order repository method and should not be moved until runtime split is complete.

## READY_FOR_REAL_USE

Not declared.
