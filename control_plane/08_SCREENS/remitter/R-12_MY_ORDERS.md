# R-12_MY_ORDERS.md

SCREEN_ID: R-12_MY_ORDERS
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
List user orders.

route:
/orders

entry points:
Bottom nav

exit points:
R-09_ORDER_TRACKING_CHAT

data required:
- authenticated user/session
- own orders from GET /api/v1/orders/mine

endpoint used:
- GET /api/v1/orders/mine

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
None / contextual

validation:
none

permissions:
own orders only

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none

privacy:
- List shows masked/summary order data only.
- Do not reveal full payment instructions.
- Link to R-07 for full payment instructions only when order is own `waiting_payment` and not expired.
- Link/state to R-09 belongs to slice 07.
- Active order chats may be opened from this list. Completed and cancelled
  orders keep their public order code but do not require a reopen-chat action.
- Do not expose account_value, storage paths or private business data.

QA checklist:
Empty state if none
