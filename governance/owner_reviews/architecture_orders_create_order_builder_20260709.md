# Architecture Review - Orders Create Order Builder

## Status

PASSED_AFTER_REFACTOR

## Scope

Surgical backend refactor of order creation preparation logic.

## Files changed

- `apps/api/app/modules/orders/create_order_builder.py`
- `apps/api/app/modules/orders/service.py`

## What changed

- Extracted create-order payload preparation into `create_order_builder.py`.
- Moved payment snapshot creation out of `OrdersService`.
- Moved initial state event and audit event preparation out of `OrdersService`.
- Kept repository calls, validations, idempotency check, credit/ad effects, state event persistence, audit write order and API behavior unchanged.

## Measurements

- `apps/api/app/modules/orders/service.py`: 834 lines.
- `OrdersService.create_order`: 86 lines.
- `apps/api/app/modules/orders/create_order_builder.py`: 116 lines.
- `build_create_order_plan`: 70 lines.
- `bind_created_order_to_audit_events`: 10 lines.

## Validation

- `python -m pytest apps\api\tests\test_order_creation.py apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_business_order_ops.py -q`
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

- `create_order` is now smaller, but still owns orchestration: validation, idempotency, repository effects and audit dispatch.
- Next safe backend candidates are `report_payment` and `confirm_business_payment`, because they still contain several responsibilities in one method.

## READY_FOR_REAL_USE

Not declared.
