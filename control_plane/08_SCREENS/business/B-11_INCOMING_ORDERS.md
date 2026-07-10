# B-11_INCOMING_ORDERS.md

SCREEN_ID: B-11_INCOMING_ORDERS
actor: business
slice: slice_06_business_order_ops
status: DRAFT_CONTROLLED

purpose:
List incoming orders for the owner business.

route:
/business/orders

entry points:
Dashboard

exit points:
B-12_BUSINESS_ORDER_DETAIL

data required:
- authenticated user/session
- `GET /api/v1/business/orders`
- data defined by `BUSINESS_ORDERS_API.md`

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.
- Use cursor pagination.

write strategy:
- No writes from this screen.
- Writes only through approved API endpoints from detail.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
None

validation:
none

permissions:
own business orders only; backend validates `business_owner`, approved business and `orders.business_id`.

states:
- loading
- empty
- error
- offline
- forbidden
- success where applicable

audit events:
none

slice boundary:
- This screen belongs to slice 06.
- Slice 04 must not build incoming business order operations except documentation references.
- Chat, disputes and remitter confirm-received are out of scope.

QA checklist:
- filters by status
- cursor pagination
- does not show foreign orders
- does not expose `storage_path`, `account_value` or full payment instructions

## Slice 14B1 access contract

- Requires `surface/session` allowed for `business_mini_app`.
- Suspended business may view history/open cases only if backend capabilities allow.
- Blocked business, blocked user or blocked/revoked link cannot operate incoming orders.
