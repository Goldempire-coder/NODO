# Architecture - Client Screens Split

Status: PASSED_AFTER_FIX

## Objective

Remove the remaining client frontend screen monolith by splitting `RemitterScreens.tsx` into small flow-specific screen files.

## Problem Corrected

Before this cut, `apps/web/src/screens/client/RemitterScreens.tsx` rendered most client views in one large component.

It included:

- welcome
- terms
- client profile setup
- profile
- marketplace search
- marketplace list
- marketplace detail
- create order
- order summary
- payment instructions
- report payment
- my orders
- messages

That made the Client Mini App harder to maintain and risky to polish.

## Files Created

- `apps/web/src/screens/client/RemitterScreens.types.ts`
- `apps/web/src/screens/client/ClientOnboardingScreens.tsx`
- `apps/web/src/screens/client/ClientMarketplaceScreens.tsx`
- `apps/web/src/screens/client/ClientOrderScreens.tsx`
- `apps/web/src/screens/client/ClientPaymentScreens.tsx`

## File Updated

- `apps/web/src/screens/client/RemitterScreens.tsx`

## Resulting File Sizes

```txt
ClientMarketplaceScreens.tsx: 164
ClientOnboardingScreens.tsx: 93
ClientOrderScreens.tsx: 131
ClientPaymentScreens.tsx: 106
ClientScreens.tsx: 85
ClientWorkspace.tsx: 8
ClientWorkspaceShell.tsx: 168
RemitterScreens.tsx: 15
RemitterScreens.types.ts: 59
```

## Responsibility Split

`RemitterScreens.tsx` is now only a router/composer.

Responsibilities moved:

- onboarding/profile -> `ClientOnboardingScreens.tsx`
- marketplace/search/detail -> `ClientMarketplaceScreens.tsx`
- create order/order summary/my orders/messages -> `ClientOrderScreens.tsx`
- payment instructions/report payment -> `ClientPaymentScreens.tsx`
- shared model type and `displayBusinessName` -> `RemitterScreens.types.ts`

## Security / Boundary Scan

```txt
CLIENT_SCREEN_SENSITIVE_SCAN_OK
```

Checked for:

- `BusinessMiniAppWorkspace`
- `AdminWebWorkspace`
- `/api/v1/admin`
- `/api/v1/businesses/me`
- `storage_path`
- `account_value`
- `escrow`
- `fondos protegidos`
- `pago garantizado`
- `garantia de entrega`
- `garantía de entrega`

No hits in `apps/web/src/screens/client`.

## Validation

```txt
corepack pnpm --filter @nodo/web build
PASS

$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
133 passed, 1 warning

python -m ruff check apps\api scripts
PASS

python -m compileall apps\api scripts
PASS
```

Known warning:

```txt
StarletteDeprecationWarning from fastapi.testclient/httpx
```

## Not Changed

- No backend behavior changed.
- No API endpoints changed.
- No payloads changed.
- No business rules changed.
- No copy intentionally changed.
- No CSS/layout intentionally changed.
- No deploy executed.
- No real-service configuration changed.
- No `READY_FOR_REAL_USE` declared.

## Residual Risk

The next architecture cleanup should move to backend runtime complexity, not frontend screens.

Recommended next target:

```txt
apps/api/app/modules/business_intake/service.py
```

Reason:

The business intake bot has real user-facing conversation edge cases, and `process_telegram_update` plus `_handle_text_step` are still concentrated in one service.
