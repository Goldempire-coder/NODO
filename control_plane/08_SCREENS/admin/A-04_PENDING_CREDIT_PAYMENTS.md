# A-04_PENDING_CREDIT_PAYMENTS.md

SCREEN_ID: A-04_PENDING_CREDIT_PAYMENTS
actor: admin
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

slice_09_note:
Slice 09 may link to or embed this screen in admin navigation, but ownership and
business logic remain in slice_08_credits_referrals.

purpose:
List credit purchases pending manual review.

route:
/admin/credits/pending

entry points:
Dashboard

exit points:
A-05_CREDIT_PAYMENT_DETAIL

data required:
- authenticated user/session
- `GET /api/v1/admin/credit-purchases`
- pending manual review purchases with masked proof metadata

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
None

validation:
none

permissions:
admin/super_admin; support read-only if enabled by RBAC

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none

QA checklist:
- Queue works.
- Does not expose `storage_path`.
- Support cannot approve/reject.
