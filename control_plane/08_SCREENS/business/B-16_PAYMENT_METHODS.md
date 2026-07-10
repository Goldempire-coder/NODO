# B-16_PAYMENT_METHODS.md

SCREEN_ID: B-16_PAYMENT_METHODS
actor: business
slice: business_app
status: DRAFT_CONTROLLED

purpose:
Read official approved Zelle/USDT methods for the business.

scope note:
In 14B this screen is read-only or a governed placeholder. The business cannot create, edit, approve, disable or delete payment methods from the Mini App Negocio.

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
- No writes in 14B.
- Method creation, edit, approval, disable and delete are admin-controlled outside this business mini app scope.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
None in 14B.

validation:
- Only display backend-approved active methods.
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
none for normal read; denied access may audit surface_access_denied

QA checklist:
Sensitive data masked
No create/edit/delete controls in 14B
No manual payment_method_id input
No account_value display
No storage_path display
