# client smoothness pass - 2026-07-07

Estado: `STAGING_DEPLOYED_FOR_OWNER_REVIEW`

No se declara `READY_FOR_REAL_USE`.

## Motivo

Owner reporto que algunas pantallas tardaban en abrir y la Mini App Cliente no se sentia smooth.

## Hallazgo

- Cloudflare respondia rapido.
- Backend `/ready` tarda alrededor de 1s porque valida DB/Redis.
- Varias vistas cliente dependian de fetch vivo al tocar tabs o abrir detalle.
- La UI cambiaba de pantalla, pero no tenia cache local corto ni prefetch de marketplace/ordenes.

## Cambios

- `useClientMarketplaceModel.ts`
  - cache local de 30s para busquedas/lista de negocios.
  - prefetch de marketplace activo.
  - detalle de negocio optimista si el anuncio ya esta en lista.
- `useRemitterOrdersModel.ts`
  - cache local de 30s para mis ordenes/mensajes.
  - prefetch de ordenes.
  - detalle de orden optimista si ya esta en lista.
- `useClientWorkspaceModel.ts`
  - warmup en background despues de entrar a la superficie cliente.

## Validacion

- Frontend build: `PASS`
- Backend pytest: `100 passed, 1 warning`
- Ruff: `PASS`
- Bundle publicado:
  - chunk: `/_next/static/chunks/app/page-4cd28c823d81398b.js`
  - API base Railway presente: `true`
  - `/api/v1/business`: `false`
  - `/api/v1/admin`: `false`
  - `create-ad`: `false`
  - `business-chat`: `false`
  - prefetch/cache presente: `true`

## Deploy

- Cloudflare preview: `https://74e98b85.nodo-staging.pages.dev`
- Canonical: `https://nodo-staging.pages.dev`
- Bot menu URL: `https://nodo-staging.pages.dev/?tg_v=20260707162522`

## Backend publico

- `/ready`: `ready`
- database: `true`
- redis: `true`

## Pendiente

- Probar en Telegram real con usuario owner.
- Si todavia se siente lento al abrir instrucciones/chat, medir esos endpoints autenticados desde una sesion real.
