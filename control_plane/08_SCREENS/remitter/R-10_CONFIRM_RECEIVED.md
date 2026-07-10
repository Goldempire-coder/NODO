# R-10_CONFIRM_RECEIVED.md

SCREEN_ID: R-10_CONFIRM_RECEIVED
actor: remitter
slice: slice_09_or_slice_10_future_contract
status: DRAFT_CONTROLLED

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
- data defined by future API contract for this screen

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
Confirmar recibido

validation:
checklist confirmed

permissions:
own order delivered

slice boundary:
- This screen is outside slice 06.
- This screen is outside slice 07.
- This screen is outside slice 10 unless a future contract explicitly assigns
  manual remitter confirmation to slice 10.
- Slice 06 may set order `delivered`, but must not build remitter confirmation.
- Slice 07 may link to chat/dispute, but must not build remitter confirmation, completion, rating or auto-complete.
- Slice 10 may auto-complete `delivered` orders by timer, but must not build
  this manual confirmation screen.
- Exact owner slice must be defined by future contract before build.

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
order_completed

QA checklist:
Shows bank-reflected warning
