# B-17_BUSINESS_SETTINGS.md

SCREEN_ID: B-17_BUSINESS_SETTINGS
actor: business
slice: business_app
status: DRAFT_CONTROLLED

purpose:
Business settings.

route:
/business/settings

entry points:
Dashboard

exit points:
B-04_BUSINESS_DASHBOARD

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
Guardar cambios

validation:
allowed fields only

permissions:
own business

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
business_updated optional

QA checklist:
Cannot alter risk limits

## Slice 14B1 access contract

- Requires `surface/session` response for `business_mini_app`.
- Show access link status if backend exposes safe metadata.
- Do not allow self-link, self-reactivate, self-approve or self-unblock.
- If link is suspended/revoked/blocked, show contact NODO state only.
