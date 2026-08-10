# B-12_BUSINESS_ORDER_DETAIL.md

SCREEN_ID: B-12_BUSINESS_ORDER_DETAIL
actor: business
slice: slice_06_business_order_ops
status: DRAFT_CONTROLLED

purpose:
Confirm payment, reject payment report, and mark delivered for own business order.

route:
/business/orders/:id

entry points:
Incoming orders

exit points:
B-13_BUSINESS_CHAT link/state only toward slice 07

data required:
- authenticated user/session
- `GET /api/v1/business/orders/{id}`
- data defined by `BUSINESS_ORDERS_API.md`

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.
- Confirm, open-dispute and deliver require backend idempotency.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Contextual by status:
- `payment_reported`: confirm payment or report a payment problem.
- `payment_confirmed`: mark delivered.

validation:
status-specific:
- confirm payment requires `payment_reported`.
- reporting a payment problem requires `payment_reported` and structured reason
  `payment_not_received_or_incomplete`.
- mark delivered requires `payment_confirmed`.

permissions:
own business order only; backend validates `business_owner`, approved business and `orders.business_id`.

states:
- loading
- empty
- error
- offline
- forbidden
- success where applicable

audit events:
payment_confirmed/dispute_opened/credits_consumed/order_delivered

copy required:
- Confirmar pago significa que el negocio reconoce recepcion real del pago.
- Confirmar recepcion consume creditos del anuncio.
- Confirmar recepcion archiva el anuncio; la orden sigue viva para entrega.
- Enviar pago movil es una accion separada.
- Marcar entregado significa que el negocio dice que envio el pago movil.
- NODO registra evidencia y estado; no retiene fondos.
- Reportar problema con pago abre una disputa, mantiene la conversacion
  investigable y no libera anuncio, credito ni capacidad.

scope boundary:
- This screen belongs to slice 06.
- Chat is not built here; B-13 is only a link/state toward slice 07.
- Confirm received by remitter is not built here.
- Auto-complete is not built here.

QA checklist:
- cannot confirm other business order
- confirm-payment consumes credits exactly once
- confirm-payment archives ad and does not return it to marketplace
- payment-problem dispute does not consume credits and keeps ad in_order
- mark-delivered does not complete order
- no `storage_path`, `account_value` or full payment instructions exposed

## Slice 14B1 access contract

- Requires `surface/session` allowed for `business_mini_app`.
- Mutating actions require active business link and capabilities from backend.
- Suspended business may respond to open cases only if explicitly returned by capabilities.
- Blocked business/link/user cannot confirm payment, open a payment-problem dispute or mark delivered.
