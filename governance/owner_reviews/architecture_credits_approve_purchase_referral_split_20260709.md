# Architecture Review - Credits Approve Purchase Referral Split

## Status

PASSED_AFTER_REFACTOR

## Scope

Surgical backend refactor of Postgres credit purchase approval.

## Files changed

- `apps/api/app/modules/credits/repository.py`

## What changed

- Extracted the Postgres referral bonus block from `approve_purchase` into `_grant_referral_bonus_if_eligible_pg`.
- Kept the referral logic inside the same database transaction.
- Kept SQL statements, wallet locking, purchase locking, ledger insert, referral cap check, commit timing and return shape unchanged.

## Measurements

- `apps/api/app/modules/credits/repository.py`: 873 lines.
- In-memory `approve_purchase`: 29 lines.
- Postgres `approve_purchase`: 87 lines.
- `_grant_referral_bonus_if_eligible_pg`: 103 lines.

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

- `credits/repository.py` is still large because it contains both in-memory and Postgres implementations.
- `_grant_referral_bonus_if_eligible_pg` is still long, but isolated. It can be split further later into wallet creation, referral reward and referral rejection helpers.
- No production readiness is implied.

## READY_FOR_REAL_USE

Not declared.
