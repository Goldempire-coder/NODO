# UI_CONTRACT.md

Screens affected:

- R-07_PAYMENT_INSTRUCTIONS
- R-08_REPORT_PAYMENT

Screens explicitly out of slice 05:

- R-09_ORDER_TRACKING_CHAT except link/state toward slice 07.
- Business confirmation/rejection screens.
- Chat and disputes.
- Admin override screens.

## UI rules

- Follow `07_UI_UX/VISUAL_REFERENCE.md` and `SCREEN_LAYOUT_MASTER.md`.
- Telegram Mini App mobile-first layout.
- Use `@telegram-apps/telegram-ui` where applicable.
- Respect themeParams, safe areas and MainButton.
- Include loading, empty, error, offline, forbidden and success states.
- Do not create landing/marketing pages instead of functional screens.
- Do not promise escrow, protected funds, guaranteed transaction or guaranteed delivery.

## Payment instructions screen

R-07 must:

- call `GET /api/v1/orders/{id}/payment-instructions`
- show full instructions only for the owner
- show timer/deadline
- show payment amount and order code
- provide CTA to R-08
- not create payment report

## Report payment screen

R-08 must:

- call `POST /api/v1/orders/{id}/payment-evidence` when uploading evidence
- call `POST /api/v1/orders/{id}/payment-report`
- require Zelle reference/name/proof
- require USDT tx_hash/network/payment amount
- show success as `payment_reported`
- link toward R-09/slice 07 without building chat/tracking

## Required copy

Use clear copy that communicates:

- El cliente paga directamente al negocio.
- NODO no recibe ni retiene fondos.
- NODO registra evidencia y estado de la orden.
- Reportar pago no significa que el negocio ya confirmo recepcion.
- Despues de reportar pago, el negocio debe revisar y confirmar.

Forbidden copy:

- escrow
- fondos protegidos
- garantia de entrega
- NODO recibio tu dinero
- pago garantizado
- transaccion asegurada
