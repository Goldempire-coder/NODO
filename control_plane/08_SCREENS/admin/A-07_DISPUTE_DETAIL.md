# A-07_DISPUTE_DETAIL.md

SCREEN_ID: A-07_DISPUTE_DETAIL
actor: admin
slice: slice_09_admin_console
status: DRAFT_CONTROLLED

purpose:
Resolve dispute.

route:
/admin/disputes/:id

entry points:
Disputes list

exit points:
A-06_DISPUTES_LIST

data required:
- authenticated user/session
- `GET /api/v1/admin/disputes/{id}`
- `POST /api/v1/admin/disputes/{id}/resolve`
- dispute, order summary, evidence metadata, events and messages allowed by `DISPUTES_API.md`

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
Resolve as web action for admin/super_admin only, with confirmation, reason required, idempotency and backend audit. Hidden for support and still denied by backend.

validation:
- resolution_type required
- reason required
- Idempotency-Key required

permissions:
admin/super_admin can resolve; support read-only

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
dispute_resolved

copy:
- NODO registra una decision operativa/admin.
- NODO no recibe, retiene, transfiere ni garantiza fondos.

QA checklist:
Audit and notify
