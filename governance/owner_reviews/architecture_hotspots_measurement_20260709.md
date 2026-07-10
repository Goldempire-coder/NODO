# Architecture Hotspots Measurement

## Status

READ_ONLY_MEASUREMENT

## Scope

Measured large files and long functions after the recent surgical refactors.

## Largest files

- `apps/api/app/modules/credits/repository.py`: 863 lines.
- `apps/api/app/modules/orders/repository.py`: 837 lines.
- `apps/api/app/modules/orders/service.py`: 784 lines.
- `apps/api/app/modules/businesses/repository.py`: 783 lines.
- `apps/api/app/modules/ads/repository.py`: 767 lines.
- `apps/api/app/modules/jobs/worker.py`: 677 lines.
- `apps/api/app/modules/business_intake/repository.py`: 653 lines.
- `apps/api/app/modules/businesses/service.py`: 537 lines.
- `apps/api/app/modules/ads/service.py`: 527 lines.
- `apps/web/src/screens/admin-web/AdminWebScreens.tsx`: 526 lines.
- `apps/api/app/modules/business_intake/conversation.py`: 520 lines.

## Longest backend functions

- `credits/repository.py:525 approve_purchase`: 181 lines.
- `orders/repository.py:578 confirm_business_payment_with_credit_consumption`: 135 lines.
- `disputes/service.py:202 resolve_admin_dispute`: 121 lines.
- `ads/service.py:203 create_ad`: 115 lines.
- `jobs/worker.py:55 run`: 109 lines.
- `ads/repository.py:407 publish_ad`: 82 lines.
- `users/service.py:66 login_with_telegram`: 81 lines.
- `business_intake/conversation.py:294 process_telegram_update`: 83 lines.

## Current interpretation

The recent orders service cuts helped. The remaining architecture risk is now concentrated in:

1. Repository files that contain both in-memory and Postgres implementations in one file.
2. Credit approval logic.
3. Admin dispute resolution logic.
4. Ads creation/publishing logic.
5. Jobs worker orchestration.
6. Admin Web screen composition.

## Recommended next cuts

### Priority 1: split repositories by runtime

Files like `credits/repository.py`, `orders/repository.py`, `businesses/repository.py`, `ads/repository.py` are large mostly because each file holds both in-memory and Postgres implementations. This is not a business-rule problem, but it hurts maintainability.

Recommended pattern:

- `repository.py`: shared protocol/factory only.
- `memory_repository.py`: test/local in-memory implementation.
- `postgres_repository.py`: production Postgres implementation.
- Keep method names and tests unchanged.

This is a clean architecture improvement with low product risk if done one module at a time.

### Priority 2: credits approval

`credits/repository.py:525 approve_purchase` is 181 lines and is the longest function measured. It likely mixes purchase validation, wallet update, ledger insert, purchase update and transaction handling.

Recommended cut:

- Extract ledger/wallet mutation preparation.
- Keep DB transaction in repository.
- Add focused tests around double approval, rejected purchase, ledger amount and wallet balances.

### Priority 3: admin dispute resolution

`disputes/service.py:202 resolve_admin_dispute` is 121 lines and touches orders, credits, ads and audit. This is high business risk.

Recommended cut:

- First only extract resolution metadata/event/response builders.
- Do not move state effects until concurrency tests are added.

### Priority 4: ads create/publish

`ads/service.py:create_ad` and `ads/repository.py:publish_ad` are still large. These affect marketplace and credit holds.

Recommended cut:

- Extract ad validation/plan builder first.
- Keep credit hold transaction unchanged.

### Priority 5: Admin Web screens

`AdminWebScreens.tsx` is 526 lines. It is acceptable for a first split, but should not keep growing.

Recommended cut:

- Split into `Dashboard`, `Businesses`, `Orders`, `Disputes`, `Credits`, `Intake`, `Jobs`.
- No visual redesign in the same cut.

## Do not cut next

- Do not refactor all repositories at once.
- Do not move credit-consumption transaction logic without concurrency tests.
- Do not redesign UI while splitting components.
- Do not merge business/client/admin surfaces again.

## Suggested next action

Start with `credits/repository.py` measurement and split plan, because it has the largest file and longest function. Build should be done in a separate step after reading the exact code.

## READY_FOR_REAL_USE

Not declared.
