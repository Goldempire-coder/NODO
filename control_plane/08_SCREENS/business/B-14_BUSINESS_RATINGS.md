# B-14_BUSINESS_RATINGS.md

SCREEN_ID: B-14_BUSINESS_RATINGS
actor: business
slice: business_app
status: DRAFT_CONTROLLED

purpose:
View ratings.

route:
/business/ratings

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
None

validation:
none

permissions:
own business

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none

QA checklist:
Shows rating summary
