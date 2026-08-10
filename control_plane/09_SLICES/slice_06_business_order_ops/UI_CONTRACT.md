# UI_CONTRACT.md

Screens affected by `slice_06_business_order_ops`:

- `B-11_INCOMING_ORDERS`
- `B-12_BUSINESS_ORDER_DETAIL`

Out of scope:

- `B-13_BUSINESS_CHAT`, salvo link/estado hacia slice 07.
- `R-09_ORDER_TRACKING_CHAT`.
- `R-10_CONFIRM_RECEIVED`.

## UI rules

- Follow `07_UI_UX/VISUAL_REFERENCE.md` and `SCREEN_LAYOUT_MASTER.md`.
- Telegram Mini App mobile-first layout.
- Use `@telegram-apps/telegram-ui` where practical.
- Respect themeParams, safe areas and MainButton.
- Include loading, empty, error, offline, forbidden and success states.
- Use required disclaimers for payments, verification, credits and responsibility.
- Do not create landing/marketing pages instead of functional screens.

## Required copy

- Confirmar pago significa que el negocio reconoce recepcion real del pago.
- Confirmar recepcion consume creditos del anuncio.
- Enviar pago movil es una accion separada.
- Marcar entregado significa que el negocio dice que envio el pago movil.
- NODO registra evidencia y estado; no retiene fondos.
- `Reportar problema con pago` abre una disputa investigable y no libera
  anuncio, credito ni capacidad.

## Prohibited copy

- escrow
- fondos protegidos
- garantia de entrega
- NODO recibio tu dinero
- pago garantizado
- transaccion asegurada
