# Architecture P1.8 - Admin Credits Hook

Status: PASSED_AFTER_FIX

## Objective

Reduce `useAdminWebModel.ts` by moving Admin Web credit purchase and credit adjustment logic into a focused hook.

## Problem Corrected

`apps/web/src/hooks/useAdminWebModel.ts` still owned credit purchase state, manual payment review actions, and admin credit adjustment actions.

That made the Admin Web model harder to reason about and increased the risk of future Frankenstein coupling between dashboard, business review, orders, disputes, audit logs and credits.

## Files Changed

- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/hooks/admin-web/useAdminCreditsModel.ts`

## Responsibility Moved

Moved into `useAdminCreditsModel.ts`:

- `creditPurchases`
- `selectedCreditPurchase`
- `creditFilter`
- `adjustmentBusinessId`
- `adjustmentAmount`
- `adjustmentDirection`
- `loadCreditPurchases`
- `reviewCreditPurchase`
- `submitAdjustment`

`useAdminWebModel.ts` now composes the credits hook and re-exports the same model fields expected by the existing Admin Web screens.

## Evidence

Line counts:

- `apps/web/src/hooks/useAdminWebModel.ts`: 239 lines
- `apps/web/src/hooks/admin-web/useAdminCreditsModel.ts`: 108 lines

Targeted scan:

```txt
NO_CREDITS_LOGIC_IN_MAIN_MODEL
```

Scan pattern:

```txt
listAdminCreditPurchases|reviewAdminCreditPurchase|submitAdminCreditAdjustment|const \[creditPurchases|const \[selectedCreditPurchase|const \[creditFilter|const \[adjustmentBusinessId|const \[adjustmentAmount|const \[adjustmentDirection|const loadCreditPurchases|const reviewCreditPurchase|const submitAdjustment
```

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
- No endpoints changed.
- No payloads changed.
- No UI layout changed.
- No copy/disclaimers changed.
- No deploy executed.
- No real-service configuration changed.
- No `READY_FOR_REAL_USE` declared.

## Residual Risk

`useAdminWebModel.ts` still owns audit log state/action. Next clean cut should extract audit logs into `useAdminAuditLogsModel.ts`, then leave `useAdminWebModel.ts` as a smaller composer.
