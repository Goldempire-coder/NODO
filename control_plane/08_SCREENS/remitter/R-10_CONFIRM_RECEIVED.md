# R-10_CONFIRM_RECEIVED.md

SCREEN_ID: R-10_CONFIRM_RECEIVED
actor: remitter
slice: slice_50B1_future_runtime
status: CONTRACTED_NOT_IMPLEMENTED

purpose:
Confirm receptor received pago movil.

route:
/orders/:id/confirm

entry points:
Tracking delivered

exit points:
R-11_RATING

data required:
- authenticated user/session
- own order in `delivered`
- no dispute in `open|in_review`
- backend capabilities for receipt confirmation and rating

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- `POST /api/v1/orders/{id}/confirm-received`
- `Idempotency-Key` required.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Confirmar recibido

validation:
- show a short confirmation that the receiver actually received Pago Movil
- never infer receipt from chat text
- disable only the confirmation action while its request is in flight

permissions:
- active remitter owner
- own order in `delivered`
- no dispute `open|in_review`

slice boundary:
- This screen is outside slice 06.
- This screen is outside slice 07.
- Slice 06 may set order `delivered`, but must not build remitter confirmation.
- Slice 07 may link to chat/dispute, but must not build remitter confirmation, completion, rating or auto-complete.
- Slice 50B0 defines the contract only.
- Slice 50B1 may implement this manual confirmation screen and endpoint.
- Auto-complete scheduler activation remains a separate operational slice.

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
- `order_completed` with IDs, actor, `completion_reason` and request context
- never receiver details, message bodies or payment instructions

effects:
- `delivered -> completed`
- `completion_reason = manual_confirmed`
- consume operational capacity exactly once
- do not consume publication credit again
- enable rating only when the rating contract permits it
- notify the business with generic copy

QA checklist:
- Shows bank-reflected warning.
- Cannot confirm another user's order.
- Cannot confirm before `delivered`.
- Open/in-review dispute blocks confirmation.
- Double tap/replay does not duplicate capacity, event, audit or notification.
- Failure preserves the current screen and offers a safe retry.
