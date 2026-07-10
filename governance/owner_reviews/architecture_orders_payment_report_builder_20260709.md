# Architecture Review - Orders Payment Report Builder

## Status

PASSED_AFTER_REFACTOR

## Scope

Surgical backend refactor of payment report preparation logic.

## Files changed

- `apps/api/app/modules/orders/payment_report_builder.py`
- `apps/api/app/modules/orders/service.py`

## What changed

- Extracted payment report validation and planning into `payment_report_builder.py`.
- Moved evidence ownership/resource validation out of `OrdersService.report_payment`.
- Moved state-event metadata and audit metadata creation out of `OrdersService.report_payment`.
- Kept repository writes, order state transition, idempotency behavior, policy checks and API response shape unchanged.

## Measurements

- `apps/api/app/modules/orders/service.py`: 804 lines.
- `OrdersService.report_payment`: 63 lines.
- `apps/api/app/modules/orders/payment_report_builder.py`: 99 lines.
- `build_payment_report_plan`: 52 lines.
- `payment_report_state_metadata`: 8 lines.
- `payment_report_audit_metadata`: 8 lines.

## Validation

- `python -m pytest apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_order_creation.py -q`
  - Result: 23 passed, 1 warning.
- `python -m pytest apps\api\tests -q`
  - Result: 133 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Result: passed.
- `python -m compileall apps\api scripts`
  - Result: passed.
- `corepack pnpm --filter @nodo/web build`
  - Result: passed.

## Residual risk

- `report_payment` still owns the transaction orchestration: idempotency, order loading, policy check, repository writes and audit dispatch.
- Next safe candidate is `confirm_business_payment`, because it still mixes business access, atomic/non-atomic confirmation path, credit consumption, state events, audit events and response shaping.

## READY_FOR_REAL_USE

Not declared.
