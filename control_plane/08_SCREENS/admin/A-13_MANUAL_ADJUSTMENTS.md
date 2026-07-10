# A-13_MANUAL_ADJUSTMENTS.md

SCREEN_ID: A-13_MANUAL_ADJUSTMENTS
actor: admin
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

slice_09_note:
Slice 09 may link to or embed this screen in admin navigation, but ownership and
business logic remain in slice_08_credits_referrals.

purpose:
Manual credit adjustments.

route:
/admin/adjustments

entry points:
Dashboard

exit points:
Dashboard

data required:
- authenticated user/session
- `POST /api/v1/admin/credits/adjust`
- target business wallet

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.

Admin Web desktop rules:
- Use NODO design tokens and admin web components.
- Desktop-first layout with sidebar navigation and administrative top bar.
- Use dense but legible cards, filters, tables and split/detail panels where applicable.
- No Telegram Mini App shell, no Telegram bottom nav and no Telegram MainButton.

Primary action behavior:
Apply adjustment as web button with confirmation, reason required, idempotency and backend audit.

validation:
- reason required
- admin/super_admin only
- adjustment cannot make wallet negative unless future contract allows it

permissions:
admin/super_admin

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
admin_credit_adjustment

QA checklist:
- Double confirmation.
- Uses `credits_ledger.type = admin_adjustment`.
- Support cannot adjust credits.
