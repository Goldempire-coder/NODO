# slice_14A_client_surface_cleanup Evidence

## Estado

READY_FOR_OWNER_REVIEW

## Implementacion

La Mini App Cliente ahora monta una superficie cliente separada desde `AuthEntryPage`, con allowlist de vistas y modelo cliente propio. La superficie cliente no importa ni renderiza pantallas de verificacion de negocio, operaciones de negocio ni consola admin.

## Archivos clave

- `apps/web/src/constants/clientViews.ts`: allowlist cliente con 14 vistas permitidas.
- `apps/web/src/hooks/useClientWorkspaceModel.ts`: modelo cliente de 147 lineas sin handlers negocio/admin.
- `apps/web/src/hooks/workspace/useClientTelegramMainButton.ts`: MainButton solo para crear orden y reportar pago.
- `apps/web/src/screens/client/ClientWorkspace.tsx`: wrapper de superficie cliente.
- `apps/web/src/screens/client/ClientWorkspaceShell.tsx`: shell cliente con bottom nav Inicio, Negocios, Ordenes, Mensajes, Perfil.
- `apps/web/src/screens/client/ClientScreens.tsx`: render cliente/remitente y order-chat.
- `apps/web/src/screens/auth/AuthEntryPage.tsx`: monta `ClientWorkspace`.
- `apps/web/src/screens/business/RemitterScreens.tsx`: props acotadas a modelo cliente/remitente.
- `apps/web/src/hooks/useBusinessWorkspaceModel.ts`: alias `openOrderChat` para compatibilidad del workspace mixto guardado para slices posteriores.

## Lo que salio de Mini App Cliente

- onboarding
- verification
- pending
- business-orders
- business-order-detail
- business-chat
- create-ad
- my-ads
- archived-ads
- credits-dashboard
- buy-credits
- credit-payment-pending
- credits-ledger
- referrals
- admin-list
- admin-detail
- admin-dashboard
- admin-metrics
- admin-orders
- admin-order-detail
- admin-disputes
- admin-dispute-detail
- admin-audit-logs
- admin-credit-purchases
- admin-credit-detail
- admin-credit-adjustments

## Lo que quedo dentro

- welcome
- terms
- client-profile-setup
- profile
- marketplace-search
- marketplace-list
- marketplace-detail
- create-order
- order-summary
- payment-instructions
- report-payment
- my-orders
- messages
- order-chat

## Validaciones

- Frontend build inicial: PASSED, Next.js compilado correctamente.
- Frontend build staging con `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME`: PASSED.
- Ruff: PASSED.
- Compileall: PASSED.
- Pytest acumulado backend: PASSED, `100 passed, 1 warning in 14.38s`.
- Scan imports prohibidos cliente: PASSED, sin matches.
- Scan handlers negocio/admin en modelo cliente: PASSED, sin matches.
- Scan frontend source/build de secretos, `storage_path`, `account_value` y claims prohibidos: PASSED, sin matches.

## Deploy

No ejecutado. No hay `wrangler`/script Cloudflare Pages en el repo ni variables `CLOUDFLARE*`, `CF_*` o `BOT_TOKEN` disponibles en esta sesion. No se hizo deploy backend.

## Riesgos residuales

- Deploy Cloudflare Pages y actualizacion de menu Telegram quedan pendientes de credenciales/tooling del owner.
- Warning preexistente de Tailwind: `content` option missing or empty.
- Warning preexistente de Starlette/httpx en tests.

## Confirmaciones

- No backend modificado.
- No migraciones modificadas.
- No endpoints modificados.
- No contratos modificados.
- No Mini App Negocio construida.
- No Admin Web construido.
- No Bot Registro construido.
- No soporte completo construido.
- No READY_FOR_REAL_USE declarado.
