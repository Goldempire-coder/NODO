# R-06_ORDER_SUMMARY.md

SCREEN_ID: R-06_ORDER_SUMMARY
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
Confirm order before locking ad.

route:
/orders/summary

entry points:
Create order

exit points:
R-07_PAYMENT_INSTRUCTIONS

data required:
- authenticated user/session
- ad_id
- amount_usd
- receiver_data
- frozen rate preview from ad detail
- calculated Bs preview
- masked payment instruction summary only

endpoint used:
- POST /api/v1/orders

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
Confirmar y crear orden

validation:
all order data valid

permissions:
remitter active

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
order_created

write contract:
- POST /api/v1/orders requires Idempotency-Key.
- Successful create persists `waiting_payment`.
- Create moves ad to `in_order`.
- Create does not reveal full payment instructions.
- Create does not consume credits.

exit points:
- R-12_MY_ORDERS or disabled/link state toward R-07 in slice 05.

QA checklist:
Creates order once; handles ad not available
