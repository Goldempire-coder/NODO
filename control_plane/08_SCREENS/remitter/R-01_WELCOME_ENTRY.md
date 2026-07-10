# R-01_WELCOME_ENTRY.md

SCREEN_ID: R-01_WELCOME_ENTRY
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
Entry screen from bot/start.

route:
/

entry points:
Bot /start

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
- Use AnimatedLogo according to MOTION_AND_INTERACTION.md.
- Respect reduced motion.

MainButton behavior:
Open NODO

motion:
- logo intro 900ms-1400ms
- fade/scale entry
- verification/check accent pulse once
- no infinite decorative loop
- must finish in stable logo state

validation:
No form validation

permissions:
remitter active or create profile

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
user_created optional

QA checklist:
Opens app; respects terms gate
