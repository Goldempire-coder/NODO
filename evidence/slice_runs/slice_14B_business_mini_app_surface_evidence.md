# Evidence - slice_14B_business_mini_app_surface

Generated at: 2026-07-07T17:47:31.9909329-04:00

## Build evidence
Command:
`corepack pnpm --filter @nodo/web build`

Result:
- OK.
- Next.js 15.5.20.
- Compiled successfully.
- Route `/`: 26.3 kB.
- First Load JS: 129 kB.

## Backend test evidence
Command:
`$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`

Result:
- OK.
- `105 passed, 1 warning in 15.66s`.
- Warning: Starlette/httpx deprecation warning.

## Lint evidence
Command:
`python -m ruff check apps\api scripts`

Result:
- OK.
- `All checks passed!`

## Compile evidence
Command:
`python -m compileall apps scripts`

Result:
- OK.
- Python compile completed.

## Endpoint evidence
Implemented:
- `GET /api/v1/business/payment-methods`

Relevant references:
- `apps/api/app/modules/businesses/routes.py:136`
- `apps/api/app/modules/businesses/service.py:54`
- `apps/api/app/modules/businesses/service.py:290`
- `apps/api/tests/test_ads_marketplace.py:246`
- `apps/api/tests/test_ads_marketplace.py:268`

## Surface separation evidence
Implemented:
- `apps/web/src/screens/auth/AuthEntryPage.tsx:6`
- `apps/web/src/screens/auth/AuthEntryPage.tsx:18`
- `apps/web/src/screens/business-app/BusinessMiniAppWorkspace.tsx:7`

Scan:
`rg -n "ClientWorkspace|RemitterScreens|AdminConsoleScreens|VerificationScreens" apps\web\src\screens\business-app apps\web\src\hooks\useBusinessMiniAppModel.ts`

Result:
- No findings.

Scan:
`rg -n "loadAdmin|reviewBusiness|openDocument|reviewCreditPurchase|submitAdminAdjustment|resolveAdminDispute|createOrder|searchAds|loadActiveMarketplace|openPaymentInstructions|submitPaymentReport" apps\web\src\hooks\useBusinessMiniAppModel.ts`

Result:
- No findings.

## Payment method UI evidence
Relevant references:
- `apps/web/src/hooks/useBusinessMiniAppModel.ts:126`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx:157`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx:165`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx:183`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx:254`

Evidence:
- Business app loads approved methods from `/api/v1/business/payment-methods`.
- Create ad uses a controlled selector.
- Empty state says: `Aun no tienes metodos aprobados. Contacta a NODO para activar tus metodos de operacion.`
- UI displays masked account only.

## Secret/private data scan
Command:
`rg -n "SUPABASE_SERVICE_ROLE_KEY|BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|STRIPE_SECRET|storage_path|account_value|escrow|fondos protegidos|pago garantizado|garantia de entrega|NODO recibio dinero" apps\web\src apps\web\.next apps\web\out`

Result:
- No findings.

## Not executed
- No deploy executed.
- No Telegram real smoke executed.
- No dedicated slice 14B runner found in `scripts`.
