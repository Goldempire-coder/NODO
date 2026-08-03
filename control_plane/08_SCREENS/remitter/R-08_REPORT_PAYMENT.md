# R-08_REPORT_PAYMENT.md

SCREEN_ID: R-08_REPORT_PAYMENT
actor: remitter
slice: slice_05_payment_instructions_reports
status: DRAFT_CONTROLLED

purpose:
Mark payment sent for an own `waiting_payment` order, with optional proof.

route:
/orders/:id/report

route note:
This is a frontend route. API calls must use `/api/v1`.

entry points:
Payment instructions

exit points:
R-09_ORDER_TRACKING_CHAT link/state toward slice 07 only.

data required:
- authenticated user/session
- order from `GET /api/v1/orders/{id}` or payment instructions context
- payment method from order snapshot
- optional evidence file when the client chooses to attach it

endpoint used:
- POST /api/v1/orders/{id}/payment-evidence
- POST /api/v1/orders/{id}/payment-report

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.
- `payment-report` requires `Idempotency-Key`.
- `payment-evidence` requires `Idempotency-Key`.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Confirmar y enviar

validation:
- own order
- `order.status = waiting_payment`
- order not expired
- Zelle requires the locked payment amount; proof and sender fields are optional.
- USDT requires the locked payment amount. The UI does not require a transaction hash; if the business needs extra evidence, it can ask for it in chat.

permissions:
own order waiting_payment

states:
- loading
- empty
- error
- offline
- forbidden
- success

audit events:
- payment_evidence_uploaded when evidence is uploaded
- payment_reported when report is submitted

copy:
- El cliente paga directamente al negocio.
- NODO no recibe ni retiene fondos.
- NODO registra evidencia y estado de la orden.
- Reportar pago no significa que el negocio ya confirmo recepcion.
- Despues de reportar pago, el negocio debe revisar y confirmar.

slice boundary:
- Does not confirm business receipt.
- Does not deliver pago movil.
- Does not consume credits.
- Does not build chat/disputes.
- R-09 is only a next-step link/state for slice 07.

QA checklist:
Cannot submit expired order; cannot submit foreign order; Zelle can be reported without proof; USDT can be reported without tx_hash; optional evidence remains protected; state changes to payment_reported; no credit consumption.
