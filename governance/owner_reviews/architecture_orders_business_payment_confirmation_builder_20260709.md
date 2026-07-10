# Architecture Review - Orders Business Payment Confirmation Builder

## Status

PASSED_AFTER_REFACTOR

## Scope

Surgical backend refactor of business payment confirmation response/event preparation.

## Files changed

- `apps/api/app/modules/orders/business_payment_confirmation_builder.py`
- `apps/api/app/modules/orders/service.py`

## What changed

- Extracted payment-confirmed state-event metadata into a dedicated builder.
- Extracted audit event preparation for `payment_confirmed`, `credits_consumed` and `ad_archived`.
- Extracted the public response payload for business payment confirmation.
- Kept business access checks, rate limit, idempotency, order lookup, payment report lookup, credit consumption, report update, order update and audit write order unchanged.

## Measurements

- `apps/api/app/modules/orders/service.py`: 776 lines.
- `OrdersService.confirm_business_payment`: 72 lines.
- `apps/api/app/modules/orders/business_payment_confirmation_builder.py`: 78 lines.
- `payment_confirmed_state_metadata`: 15 lines.
- `payment_confirmation_audit_events`: 40 lines.
- `business_payment_confirmation_response`: 13 lines.

## Validation

- `python -m pytest apps\api\tests\test_business_order_ops.py apps\api\tests\test_payment_instructions_reports.py -q`
  - Result: 13 passed, 1 warning.
- `python -m pytest apps\api\tests -q`
  - Result: 133 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Result: passed.
- `python -m compileall apps\api scripts`
  - Result: passed.
- `corepack pnpm --filter @nodo/web build`
  - Result: passed.

## Residual risk

- `confirm_business_payment` still owns the transaction path and keeps both atomic repository and fallback repository paths in one method. This is intentional for this cut because the credit-consumption path is critical.
- Next safe candidate is `reject_business_payment_report` or `mark_business_delivered`, both smaller and lower risk.

## READY_FOR_REAL_USE

Not declared.
