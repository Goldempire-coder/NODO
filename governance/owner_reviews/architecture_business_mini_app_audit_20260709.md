# Business Mini App Architecture Audit

Status: PASSED_WITH_UI_REFINEMENT_RECOMMENDATIONS

## Objective

Audit the Business Mini App after the Admin Web cleanup to verify whether it is cleanly separated or drifting into a Frankenstein module.

## Files Reviewed

- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/hooks/business-mini-app/*`
- `apps/web/src/screens/business-app/*`
- `apps/web/src/constants/businessViews.ts`

## Architecture Result

The Business Mini App is not currently a Frankenstein module.

The main model is already a composer:

- `useBusinessMiniAppModel.ts`: 80 lines
- `useBusinessAccessModel.ts`: 81 lines
- `useBusinessAdsModel.ts`: 94 lines
- `useBusinessOrdersModel.ts`: 78 lines
- `useBusinessCreditsModel.ts`: 152 lines
- `useBusinessChatModel.ts`: 123 lines
- `useBusinessTelegramControls.ts`: 65 lines
- `helpers.ts`: 115 lines

This is an acceptable architecture shape. The code is split by domain: access, ads, orders, credits, chat and Telegram controls.

## Screen Size Result

Business screens are also reasonably small:

- `BusinessAccessPanel.tsx`: 75 lines
- `BusinessAdsScreens.tsx`: 122 lines
- `BusinessChatScreen.tsx`: 70 lines
- `BusinessCreditsScreens.tsx`: 132 lines
- `BusinessDashboardScreen.tsx`: 34 lines
- `BusinessMiniAppScreens.tsx`: 44 lines
- `BusinessMiniAppShell.tsx`: 152 lines
- `BusinessMiniAppWorkspace.tsx`: 8 lines
- `BusinessOrdersScreens.tsx`: 65 lines
- `BusinessSettingsScreen.tsx`: 18 lines

No immediate split is required for size.

## Boundary Scan

Scan result:

```txt
BUSINESS_APP_BOUNDARY_SCAN_OK
```

Checked for:

```txt
ClientWorkspace
RemitterScreens
AdminConsoleScreens
VerificationScreens
/api/v1/businesses/me
/api/v1/admin
account_value
storage_path
escrow
fondos protegidos
pago garantizado
garantia de entrega
garantía de entrega
```

No active violations were found in:

- `apps/web/src/screens/business-app`
- `apps/web/src/hooks/business-mini-app`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`

## Good Findings

- Business Mini App uses `surface/session` through `useBusinessAccessModel`.
- It does not use `/api/v1/businesses/me` as the access gate.
- It does not import Client Workspace, Remitter screens, Admin screens or Verification screens.
- It uses approved payment methods through selector state, not manual UUID entry.
- Numeric ad fields use `sanitizeDecimalInput`.
- Business actions remain domain-separated in hooks.
- Telegram MainButton behavior is isolated in `useBusinessTelegramControls`.

## Issues / Refinements

These are UI/product refinement items, not architecture blockers:

1. `BusinessMiniAppShell.tsx` is the largest screen file at 152 lines because it owns title mapping, nav icons and shell layout. It is still acceptable, but a future polish pass could extract `BusinessBottomNav` and `BusinessTopBar`.

2. `BusinessCreditsScreens.tsx` is functionally correct but plain. Credit purchase, ledger and referrals are all in one file. It is acceptable by size, but future visual polish may split screens into separate files if they grow.

3. Some user-facing copy is functional, not premium. Example: "Carga tu balance para ver el resumen." This does not break contracts, but can be improved in a UI polish pass.

4. Manual credit inputs allow free text for reference / tx hash. This is normal for references, but should remain backend-validated and never trusted as clean input.

5. The business dashboard is compact and clean, but not yet a rich operational dashboard. This is acceptable for architecture cleanup; polish can be a separate slice.

## No Immediate Code Cut Required

Unlike Admin Web, the Business Mini App model is already well split. A structural refactor now would add churn without clear benefit.

## Recommended Next Step

Proceed with a focused Business Mini App UX polish pass, not an architecture split:

1. Improve shell polish:
   - extract `BusinessTopBar`
   - extract `BusinessBottomNav`
   - keep same visual language as client app

2. Improve dashboard:
   - show wallet summary if loaded
   - show active ads/orders quick actions
   - keep it compact and mobile-native

3. Improve screen copy:
   - make messages shorter and less mechanical
   - avoid fear language
   - keep protective NODO posture only where needed

4. Preserve security:
   - no self-onboarding
   - no admin/client imports
   - no account values/storage paths
   - no manual payment method IDs

## Validation

Read-only audit only. No code was changed.

No build/test was required for this audit because implementation was not modified.

## Final Assessment

Business Mini App architecture is acceptable and cleaner than the old mixed workspace.

Next work should be visual/UX polish and real-flow smoke testing, not another structural refactor.
