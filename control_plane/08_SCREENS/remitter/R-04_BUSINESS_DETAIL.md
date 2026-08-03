# R-04_BUSINESS_DETAIL.md

SCREEN_ID: R-04_BUSINESS_DETAIL
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
Show business/ad details before order.

route:
/businesses/:adId

entry points:
Results

exit points:
R-05_CREATE_ORDER

data required:
- authenticated user/session
- ad_id from route
- public ad detail from GET /api/v1/ads/{id}
- disclaimer returned or mapped from REQUIRED_SCREEN_DISCLAIMERS

endpoint used:
- GET /api/v1/ads/{id}

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
Continuar con este negocio

validation:
ad active

permissions:
remitter active

states:
- loading
- empty
- error
- offline
- forbidden
- success where applicable

disclaimer:
Perfil registrado en NODO. La operacion final es entre usuario y negocio.

privacy:
- Do not reveal full payment instructions until order/payment instruction slice.
- Do not expose business documents, storage paths, internal IDs, Telegram IDs or full account values.
- Detail/click does not consume credits.

audit events:
none

QA checklist:
Shows registered-profile label and disclaimer
