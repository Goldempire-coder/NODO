# R-07_PAYMENT_INSTRUCTIONS.md

SCREEN_ID: R-07_PAYMENT_INSTRUCTIONS
actor: remitter
slice: slice_05_payment_instructions_reports
status: DRAFT_CONTROLLED

purpose:
Show full business payment data and timer only to the remitter owner.

route:
/orders/:id/pay

entry points:
Order summary, My Orders

exit points:
R-08_REPORT_PAYMENT, R-12_MY_ORDERS

data required:
- authenticated user/session
- full payment instructions from GET /api/v1/orders/{id}/payment-instructions

endpoint used:
- GET /api/v1/orders/{id}/payment-instructions

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Ya realicé el pago

validation:
order waiting_payment and not expired

permissions:
own order

security:
- Full instructions only on this screen.
- Do not show full instructions in list/detail general screens.
- `GET /api/v1/orders/{id}/payment-instructions` sets `payment_data_revealed_at` and `payment_data_revealed_by`.
- This screen does not create a payment report.
- This screen does not change order status.

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
payment_instructions_viewed

copy:
- El cliente paga directamente al negocio.
- NODO no recibe ni retiene fondos.
- NODO registra evidencia y estado de la orden.
- Reportar pago no significa que el negocio ya confirmo recepcion.

slice boundary:
- Slice 04 may link to this screen or show disabled/coming-next state.
- Slice 04 must not implement full payment instruction reveal.

QA checklist:
ClosingConfirmation active; timer visible; reveal own order only; expired order blocked; audit `payment_instructions_viewed`.
