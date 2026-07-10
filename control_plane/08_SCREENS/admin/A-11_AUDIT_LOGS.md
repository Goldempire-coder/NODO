# A-11_AUDIT_LOGS.md

SCREEN_ID: A-11_AUDIT_LOGS
actor: admin
slice: slice_09_admin_console
status: DRAFT_CONTROLLED

purpose:
Audit logs viewer.

route:
/admin/audit

entry points:
Dashboard

exit points:
none

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
admin

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none

QA checklist:
Read-only
