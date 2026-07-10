# A-05_CREDIT_PAYMENT_DETAIL.md

SCREEN_ID: A-05_CREDIT_PAYMENT_DETAIL
actor: admin
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

slice_09_note:
Slice 09 may link to or embed this screen in admin navigation, but ownership and
business logic remain in slice_08_credits_referrals.

purpose:
Approve/reject manual credit purchase.

route:
/admin/credits/:id

entry points:
A-04_PENDING_CREDIT_PAYMENTS

exit points:
A-04_PENDING_CREDIT_PAYMENTS

data required:
- authenticated user/session
- `GET /api/v1/admin/credit-purchases`
- `POST /api/v1/admin/credit-purchases/{id}/approve`
- `POST /api/v1/admin/credit-purchases/{id}/reject`
- proof metadata/signed URL rules from `CREDITS_API.md`

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
Approve/Reject as web buttons with confirmation, reason required, idempotency and backend audit.

validation:
- reason required for approve/reject
- purchase must be `pending_manual_review`
- no `storage_path` display

permissions:
admin/super_admin

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
- manual_credit_payment_approved
- manual_credit_payment_rejected
- credits_added when approved

QA checklist:
- Ledger updates once.
- Reject does not credit wallet.
- Approval requires reason.
