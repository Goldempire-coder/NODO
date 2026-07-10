# BUILDER_REPORT - slice_14A_client_surface_cleanup

## Estado final

READY_FOR_OWNER_REVIEW

## Resumen

Se separo la superficie de Mini App Cliente para que `AuthEntryPage` monte un workspace cliente dedicado. La nueva superficie renderiza solo vistas cliente/remitente permitidas, conserva marketplace, ordenes, instrucciones de pago, reporte de pago, mensajes/order-chat y perfil, y deja guardado el codigo negocio/admin para 14B/14C sin importarlo ni exponerlo desde cliente.

## Archivos creados/modificados

Creados:

- `apps/web/src/constants/clientViews.ts`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/hooks/workspace/useClientTelegramMainButton.ts`
- `apps/web/src/screens/client/ClientWorkspace.tsx`
- `apps/web/src/screens/client/ClientWorkspaceShell.tsx`
- `apps/web/src/screens/client/ClientScreens.tsx`
- `evidence/slice_runs/slice_14A_client_surface_cleanup_evidence.md`
- `evidence/slice_runs/slice_14A_client_surface_cleanup_test_results.json`
- `governance/builder_reports/slice_14A_client_surface_cleanup_BUILDER_REPORT.md`

Modificados:

- `apps/web/src/screens/auth/AuthEntryPage.tsx`
- `apps/web/src/screens/business/RemitterScreens.tsx`
- `apps/web/src/hooks/useBusinessWorkspaceModel.ts`

## Que quedo dentro de Mini App Cliente

- `welcome`
- `terms`
- `client-profile-setup`
- `profile`
- `marketplace-search`
- `marketplace-list`
- `marketplace-detail`
- `create-order`
- `order-summary`
- `payment-instructions`
- `report-payment`
- `my-orders`
- `messages`
- `order-chat`

## Que salio de Mini App Cliente

- Registro/verificacion de negocio.
- Documentos de negocio.
- Crear/gestionar anuncios.
- Creditos/referrals de negocio.
- Ordenes entrantes y operaciones de negocio.
- Chat de negocio.
- Consola admin, metricas, ordenes, disputas, audit logs, credit purchases y ajustes manuales.

## Detalles tecnicos

- `clientViews.ts` define una allowlist estricta y fallback seguro a `marketplace-search`.
- `useClientWorkspaceModel.ts` compone solo terms/profile, marketplace, ordenes remitente, payment report y chat/dispute permitido para cliente.
- `ClientWorkspaceShell.tsx` expone bottom nav cliente: Inicio, Negocios, Ordenes, Mensajes, Perfil.
- `ClientScreens.tsx` reutiliza pantallas remitente y mantiene `order-chat` sin activar `business-chat`.
- `AuthEntryPage.tsx` monta `ClientWorkspace` para usuarios autenticados.
- `RemitterScreens.tsx` fue acotado para consumir un modelo estructural cliente/remitente.

## Tests ejecutados

- `corepack pnpm --filter @nodo/web build`: PASSED antes de la recuperacion del arbol de dependencias; Next.js compilo correctamente.
- Build staging con `NEXT_PUBLIC_API_BASE_URL=https://nodo-api-production.up.railway.app`, `NEXT_PUBLIC_APP_URL=https://nodo-staging.pages.dev`, `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=NODO`: PASSED usando Next local directo; compilado en 7.2s, `5/5` static pages, `2/2` export.
- `python -m ruff check apps\api scripts`: PASSED, `All checks passed!`.
- `python -m compileall -q apps scripts`: PASSED.
- `$env:PYTHONPATH='apps/api;C:\Users\carlo\AppData\Roaming\Python\Python314\site-packages'; python -m pytest apps\api\tests -q --tb=short`: PASSED, `100 passed, 1 warning in 14.38s`.

## Scans ejecutados

- Cliente no importa `VerificationScreens`, `BusinessOperationsScreens`, `AdminConsoleScreens`: PASSED, sin matches.
- Modelo/shell cliente no expone handlers negocio/admin prohibidos: PASSED, sin matches.
- Frontend source/build sin `SUPABASE_SERVICE_ROLE_KEY`, `BOT_TOKEN`, `storage_path`, `account_value` ni claims prohibidos: PASSED, sin matches.

## Deploy

No ejecutado. No hay `wrangler`, script de Cloudflare Pages ni variables `CLOUDFLARE*`, `CF_*` o `BOT_TOKEN` disponibles en esta sesion. No se hizo deploy backend.

## Riesgos residuales

- Deploy a Cloudflare Pages y actualizacion del menu del bot quedan pendientes de credenciales/tooling.
- Warning preexistente de Tailwind: `content` option missing or empty.
- Warning preexistente de Starlette/httpx en tests.

## Confirmaciones

- No modifique backend.
- No modifique migraciones.
- No modifique endpoints.
- No modifique contratos.
- No construi Mini App Negocio.
- No construi Admin Web.
- No construi Bot Registro Negocios.
- No construi soporte completo.
- No avance a 14B.
- No declare READY_FOR_REAL_USE.
