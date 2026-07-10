# CUSTOMER_MARKETPLACE_UI_FIRST_PASS - 2026-07-06

## Estado

`CUSTOMER_MARKETPLACE_UI_FIRST_PASS_DEPLOYED`

No se declara `READY_FOR_REAL_USE`.

## Motivo

El owner reportó que el frontend staging se veía genérico y mezclaba cliente, negocio y admin en la primera experiencia. Este pase prioriza que el usuario remitente entre primero a una experiencia de marketplace de cambio verificado.

## Cambios aplicados

- `apps/web/src/hooks/workspace/useWorkspaceState.ts`
  - Vista inicial autenticada cambiada a `marketplace-search`.
- `apps/web/src/screens/auth/AuthEntryPage.tsx`
  - Copy de entrada alineado a cliente: `Cambio verificado`.
- `apps/web/src/components/nodo/AnimatedLogo.tsx`
  - Logo con check visual.
- `apps/web/src/components/feedback/StatusPanel.tsx`
  - Copy de sesión en español.
- `apps/web/src/screens/business/WorkspaceShell.tsx`
  - Navegación principal simplificada: `Inicio`, `Órdenes`, `Negocio`, `Admin`.
  - Negocio/admin quedan como superficies secundarias, no como primera experiencia del cliente.
- `apps/web/src/screens/business/RemitterScreens.tsx`
  - `marketplace-search` convertido en home de cliente:
    - monto en USD
    - método Zelle/USDT
    - CTA `Ver negocios`
    - lista de negocios disponibles
    - filtros `Mejor confianza`, `Mejor tasa`, `Más rápido`
    - disclaimer de responsabilidad directa entre partes.
- `apps/web/src/app/globals.css`
  - Estilo visual NODO oscuro, mobile-first, con cards, CTA verde/azul y referencias visuales del marketplace.

## Validación ejecutada

- Frontend build: `PASS`
- Deploy Cloudflare Pages:
  - Preview: `https://e1f2e249.nodo-staging.pages.dev`
  - Alias principal verificado: `https://nodo-staging.pages.dev`
- Bundle publicado:
  - contiene backend `https://nodo-api-production.up.railway.app`
  - contiene textos marketplace: `Ver negocios para`, `Negocios disponibles`, `Mejor confianza`
  - contiene título marketplace escapado en JS como `\xbfCu\xe1nto quieres cambiar?`, renderizable por navegador como `¿Cuánto quieres cambiar?`
- Escaneo de secretos frontend build:
  - sin `SUPABASE_SERVICE_ROLE_KEY`
  - sin `STRIPE_SECRET_KEY`
  - sin `JWT_SECRET`
  - sin `JWT_REFRESH_SECRET`
  - sin `BOT_TOKEN`
  - sin `postgresql://`
  - sin `redis://`

## Pendientes honestos

- El flujo cliente queda como primera experiencia, pero pantallas internas admin/business todavía conservan labels técnicos en algunos puntos. Deben pulirse en un pase posterior.
- Falta smoke real dentro de Telegram con `@NodoCambioBot` y usuario real.
- Falta seed/staging con negocios aprobados y anuncios reales para que el marketplace muestre cards inmediatamente.
- No se hizo stress nuevo ni prueba de concurrencia en esta intervención visual.
- No se declara `READY_FOR_REAL_USE`.
