# B-16_PAYMENT_METHODS.md

SCREEN_ID: B-16_PAYMENT_METHODS
actor: business
slice: business_app
status: DRAFT_CONTROLLED

purpose:
Manage Zelle and USDT methods for the approved business.

scope note:
The business can add, edit and delete its own Zelle and USDT methods from the Mini App Negocio. Backend remains authoritative for approval status, ownership, PIN, idempotency and masking. USDT is not limited to TRC20 in this screen; the exact network is confirmed by the parties in chat before funds are sent.

route:
/business/payment-methods

entry points:
Dashboard

exit points:
B-04_BUSINESS_DASHBOARD

data required:
- authenticated user/session
- approved own business
- methods returned by `GET /api/v1/business/payment-methods`

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- Add, edit and delete only through approved API endpoints.
- All mutations require backend validation, unlocked business PIN and Idempotency-Key.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
None.

validation:
- Only display own active methods returned by backend.
- Show empty state if there are no approved methods.
- Do not allow manual IDs or self-service method management.

permissions:
approved business

states:
- loading
- empty
- error
- offline
- forbidden
- success where applicable

audit events:
business_payment_method_self_added
business_payment_method_self_updated
business_payment_method_self_deleted

QA checklist:
Sensitive data masked outside own edit context
Create/edit/delete controls require PIN and backend success
No manual payment_method_id input
No full account_value in marketplace/client responses
No storage_path display
