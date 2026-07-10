# slice_14A client surface cleanup - owner audit + deploy

Fecha: 2026-07-07

Estado: `STAGING_DEPLOYED_FOR_OWNER_REVIEW`

No se declara `READY_FOR_REAL_USE`.

## Auditoria propia

Se reviso el resultado del builder antes de deployar. Hallazgos corregidos:

- La Mini App Cliente no renderizaba negocio/admin, pero todavia arrastraba hooks compartidos con endpoints de negocio.
- El tab activo podia quedarse en `Negocios` cuando la vista volvia a `marketplace-search`.
- `RemitterScreens.tsx` seguia ubicado en `screens/business`, aunque ya era pantalla cliente.

## Cambios aplicados

- Se creo estado dedicado cliente:
  - `apps/web/src/hooks/workspace/useClientWorkspaceState.ts`
- Se creo marketplace dedicado cliente sin endpoints de negocio:
  - `apps/web/src/hooks/workspace/useClientMarketplaceModel.ts`
- Se creo chat/disputas dedicado cliente sin `business-chat`:
  - `apps/web/src/hooks/workspace/useClientChatDisputesModel.ts`
- Se creo shell nativo Telegram dedicado cliente sin dirty views de negocio/admin:
  - `apps/web/src/hooks/workspace/useClientTelegramNativeShell.ts`
- Se movio:
  - de `apps/web/src/screens/business/RemitterScreens.tsx`
  - a `apps/web/src/screens/client/RemitterScreens.tsx`
- Se corrigio nav activo de `marketplace-search` a `Inicio`.

## Verificacion local

- Frontend build: `PASS`
- Backend pytest: `100 passed, 1 warning`
- Ruff: `PASS`
- Compileall: `PASS`
- Bundle local scan:
  - `/api/v1/business`: `false`
  - `/api/v1/admin`: `false`
  - `create-ad`: `false`
  - `business-chat`: `false`

## Deploy Cloudflare Pages

Primer deploy con branch:

- Preview: `https://e27b82fd.nodo-staging.pages.dev`
- Branch alias: `https://main.nodo-staging.pages.dev`

Luego se hizo deploy directo de Pages para actualizar la URL canonica:

- Preview: `https://3fa71839.nodo-staging.pages.dev`
- Canonical: `https://nodo-staging.pages.dev`

## Verificacion publicada

JS publicado en `https://nodo-staging.pages.dev`:

- chunk: `/_next/static/chunks/app/page-a609e78deaf92569.js`
- API base Railway presente: `true`
- `/api/v1/business`: `false`
- `/api/v1/admin`: `false`
- `create-ad`: `false`
- `business-chat`: `false`

## Bot Telegram

Menu button actualizado:

- type: `web_app`
- text: `Abrir NODO`
- url: `https://nodo-staging.pages.dev/?tg_v=20260707161605`

## Backend publico

- `/health`: `ok`
- `/ready`: `ready`
- database: `true`
- redis: `true`

## Notas

- Wrangler requirio Node 22+; se uso Node 24 del runtime local de Codex.
- Wrangler mostro warning de Git `HEAD` porque el workspace no esta abierto como repo Git raiz normal, pero el deploy termino exitosamente.
- No se hizo deploy backend.
- No se declararon usuarios reales autorizados.
