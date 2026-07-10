# BUILDER_REPORT - slice_14B_business_mini_app_surface

## Estado final
READY_FOR_OWNER_REVIEW

El producto sigue sin estar READY_FOR_REAL_USE.

## Resumen de implementacion
- Se construyo la Mini App Negocio como superficie frontend separada, accesible tecnicamente con `?surface=business`.
- La Mini App Cliente sigue siendo la superficie por defecto y no muestra negocio/admin.
- Se agrego el endpoint backend canonico `GET /api/v1/business/payment-methods`.
- Crear anuncio en la superficie negocio usa selector visual de metodos aprobados por backend; no usa input manual de `payment_method_id`.
- No se construyo Admin Web, Bot Registro Negocios, soporte completo ni deploy.

## Archivos modificados o creados
- `apps/api/app/modules/businesses/service.py`
- `apps/api/app/modules/businesses/routes.py`
- `apps/api/tests/test_ads_marketplace.py`
- `apps/web/src/screens/auth/AuthEntryPage.tsx`
- `apps/web/src/types/domain.ts`
- `apps/web/src/constants/views.ts`
- `apps/web/src/constants/navigation.ts`
- `apps/web/src/constants/businessViews.ts`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/screens/business-app/BusinessMiniAppWorkspace.tsx`
- `apps/web/src/screens/business-app/BusinessMiniAppShell.tsx`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx`
- `governance/builder_reports/slice_14B_business_mini_app_surface_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_14B_business_mini_app_surface_evidence.md`
- `evidence/slice_runs/slice_14B_business_mini_app_surface_test_results.json`

## Endpoints agregados
- `GET /api/v1/business/payment-methods`

Reglas implementadas:
- Requiere JWT.
- Requiere rol `business_owner`.
- Requiere negocio propio aprobado.
- Devuelve solo metodos propios aprobados, activos y disponibles.
- Devuelve `masked_account`, `label`, `receive_display`, `delivery_display`, `delivery_currency` y limites seguros.
- No devuelve `account_value`.
- No devuelve `storage_path`.
- Devuelve lista vacia si no hay metodos aprobados.

## Pantallas agregadas
- `BusinessMiniAppWorkspace`
- `BusinessMiniAppShell`
- `BusinessMiniAppScreens`

La superficie incluye:
- dashboard negocio
- estados de acceso: loading, sin negocio, no aprobado, suspendido, bloqueado, error
- creditos
- comprar creditos / pago pendiente
- ledger de creditos
- crear anuncio con selector de metodo aprobado
- mis anuncios
- anuncios archivados
- ordenes entrantes
- detalle de orden
- chat negocio por orden
- referrals
- metodos de pago read-only
- perfil/settings negocio

## Que NO construi
- No construi Admin Web.
- No construi Bot Registro Negocios.
- No construi soporte/tickets completo.
- No cambie Mini App Cliente salvo el selector tecnico de superficie en `AuthEntryPage`.
- No cambie reglas de creditos, ordenes, anuncios, pagos, disputas ni jobs.
- No hice deploy.
- No instale dependencias.
- No declare READY_FOR_REAL_USE.

## Pruebas y validaciones ejecutadas
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK.
  - Next.js 15.5.20.
  - Ruta `/`: 26.3 kB, First Load JS 129 kB.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: OK.
  - `105 passed, 1 warning in 15.66s`.
  - Warning: Starlette/httpx deprecation ya conocido.
- `python -m ruff check apps\api scripts`
  - Resultado: OK.
  - `All checks passed!`
- `python -m compileall apps scripts`
  - Resultado: OK.
  - Compilo `apps/api/app/modules/businesses/routes.py`, `service.py` y tests modificados.

## Scans ejecutados
- `rg -n "ClientWorkspace|RemitterScreens|AdminConsoleScreens|VerificationScreens" apps\web\src\screens\business-app apps\web\src\hooks\useBusinessMiniAppModel.ts`
  - Resultado: sin hallazgos.
- `rg -n "loadAdmin|reviewBusiness|openDocument|reviewCreditPurchase|submitAdminAdjustment|resolveAdminDispute|createOrder|searchAds|loadActiveMarketplace|openPaymentInstructions|submitPaymentReport" apps\web\src\hooks\useBusinessMiniAppModel.ts`
  - Resultado: sin hallazgos.
- `rg -n "SUPABASE_SERVICE_ROLE_KEY|BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|STRIPE_SECRET|storage_path|account_value|escrow|fondos protegidos|pago garantizado|garantia de entrega|NODO recibio dinero" apps\web\src apps\web\.next apps\web\out`
  - Resultado: sin hallazgos.

## Tests agregados
- `test_business_payment_methods_endpoint_returns_only_safe_approved_own_methods`
- `test_business_payment_methods_endpoint_blocks_unapproved_business`

## Riesgos residuales
- La entrada a Mini App Negocio queda tecnicamente disponible por `?surface=business` hasta que exista routing/bot dedicado.
- No se ejecuto smoke real en Telegram.
- No se hizo deploy por instruccion del owner.
- No existe runner especifico `run_slice_14B_tests.py`; se valido con build frontend, pytest acumulado, Ruff, compileall y scans.

## Confirmaciones
- No modifique backend fuera del endpoint requerido para 14B.
- No modifique migraciones.
- No cambie endpoints existentes.
- No cambie reglas de credito, ordenes, anuncios, pagos, disputas ni jobs.
- No construi Admin Web.
- No construi Bot Registro Negocios.
- No construi soporte completo.
- No instale dependencias.
- No hice deploy.
- No declare READY_FOR_REAL_USE.
