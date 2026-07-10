# B-01_BUSINESS_ONBOARDING.md

## Slice 14 ownership update

Esta pantalla no pertenece a Mini App Cliente.

El onboarding inicial de negocios interesados se mueve contractualmente al Bot Registro Negocios y revision del Panel Admin Web Desktop. La Mini App Negocio solo se usa cuando el negocio ya esta aprobado/asociado.

No construir registro de negocio dentro de la Mini App Cliente.

SCREEN_ID: B-01_BUSINESS_ONBOARDING
actor: business applicant (non-persistent)
slice: business_intake_bot/admin_web
status: DRAFT_CONTROLLED

purpose:
Explain business onboarding and start verification.

route:
/business/onboarding

entry points:
Role switch/start

exit points:
B-02_BUSINESS_VERIFICATION_FORM

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
Comenzar verificación

validation:
none

permissions:
business applicant

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
business_registered optional

QA checklist:
No publishing before approval
