# R-05_CREATE_ORDER.md

SCREEN_ID: R-05_CREATE_ORDER
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
Collect receiver pago móvil data.

route:
/orders/create

entry points:
Business detail

exit points:
R-06_ORDER_SUMMARY

data required:
- authenticated user/session
- active ad detail from GET /api/v1/ads/{id}
- receiver pago movil fields
- amount_usd selected from search/detail context
- disclaimer from REQUIRED_SCREEN_DISCLAIMERS

endpoint used:
- POST /api/v1/orders after summary confirmation

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
Crear orden por $X

validation:
bank, phone, document, holder required

permissions:
remitter active

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none before create

disclaimer:
NODO registra la orden y la evidencia, pero no recibe ni retiene fondos. Pagaras directamente al negocio seleccionado.

privacy:
- Do not show full payment instructions on this screen.
- Do not show full account_value.
- Receiver data is collected only for order creation and must not be logged in frontend.

QA checklist:
No amount Bs input by user
