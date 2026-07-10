# Architecture Review - Orders Business Order Action Builder

## Status

PASSED_AFTER_REFACTOR

## Scope

Surgical backend refactor of simple business order action event/response preparation.

## Files changed

- `apps/api/app/modules/orders/business_order_action_builder.py`
- `apps/api/app/modules/orders/service.py`

## What changed

- Extracted payment rejection state metadata.
- Extracted payment rejection audit event and response payload.
- Extracted delivered state metadata.
- Extracted delivered audit event and response payload.
- Kept business access checks, rate limit, idempotency, order lookup, payment report lookup, state validation, repository writes and audit write order unchanged.

## Measurements

- `apps/api/app/modules/orders/service.py`: 784 lines.
- `OrdersService.reject_business_payment_report`: 40 lines.
- `OrdersService.mark_business_delivered`: 41 lines.
- `apps/api/app/modules/orders/business_order_action_builder.py`: 69 lines.
- `payment_rejected_audit_event`: 19 lines.
- `payment_rejected_response`: 13 lines.
- `delivered_audit_event`: 18 lines.
- `delivered_response`: 2 lines.

## Validation

- `python -m pytest apps\api\tests\test_business_order_ops.py apps\api\tests\test_chat_disputes.py apps\api\tests\test_jobs_notifications.py -q`
  - Result: 20 passed, 1 warning.
- `python -m pytest apps\api\tests -q`
  - Result: 133 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Result: passed.
- `python -m compileall apps\api scripts`
  - Result: passed.
- `corepack pnpm --filter @nodo/web build`
  - Result: passed.

## Residual risk

- The orders service is cleaner, but still owns multiple flows. The next cleanup should target order read/detail or evidence upload only if tests remain strong.
- No production readiness is implied by this refactor.

## READY_FOR_REAL_USE

Not declared.
