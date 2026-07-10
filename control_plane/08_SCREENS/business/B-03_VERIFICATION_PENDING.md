# B-03_VERIFICATION_PENDING.md

## Slice 14 ownership update

Esta pantalla no pertenece a Mini App Cliente.

Estados de solicitud/intake y revision admin se muestran en Bot Registro Negocios o Panel Admin Web Desktop segun contrato. La Mini App Negocio solo permite acceso operativo al negocio aprobado/asociado.

SCREEN_ID: B-03_VERIFICATION_PENDING
actor: business applicant (non-persistent)
slice: business_intake_bot/admin_web
status: DRAFT_CONTROLLED

purpose:
Show pending approval state.

route:
/business/pending

entry points:
Verification form

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
pending business

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none

QA checklist:
No create ad CTA
