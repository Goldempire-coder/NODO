# R-13_PROFILE.md

SCREEN_ID: R-13_PROFILE
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
User profile and terms.

route:
/profile

entry points:
Bottom nav

exit points:
R-02_HOME_SEARCH

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
own profile

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none

QA checklist:
Shows terms acceptance status
