# R-09_ORDER_TRACKING_CHAT.md

SCREEN_ID: R-09_ORDER_TRACKING_CHAT
actor: remitter
slice: slice_07_chat_disputes
status: DRAFT_CONTROLLED

purpose:
Track order status and chat.

route:
/orders/:id

route note:
This is a frontend route for slice 07. Slice 05 and slice 06 may only link to this screen or show a next-step state. They must not build chat/dispute behavior.

entry points:
Report payment, My Orders

exit points:
dispute

data required:
- authenticated user/session
- data defined by API contract for this screen

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
Contextual by backend capabilities.

Slice 07 may show:
- send message
- upload attachment
- open dispute when allowed

Slice 07 must not show:
- confirm received
- complete order
- rate business

validation:
none

permissions:
own order

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
- message_created
- message_attachment_uploaded
- dispute_opened
- dispute_message_created when applicable

slice boundary:
- R-10_CONFIRM_RECEIVED is not in slice 07.
- Completion, rating and auto-complete are future slice scope.
- NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos.

QA checklist:
Stepper uses human statuses
- no `message_sent` audit event
- no completion/rating controls
- no `storage_path`
