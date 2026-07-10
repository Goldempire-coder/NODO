# B-02_BUSINESS_VERIFICATION_FORM.md

## Slice 14 ownership update

Esta pantalla no pertenece a Mini App Cliente.

La captacion documental inicial de negocios referidos/interesados se gobierna por `BUSINESS_INTAKE_BOT_FLOW.md`, `BUSINESS_INTAKE_API.md` y Panel Admin Web Desktop.

La Mini App Negocio no puede permitir autoaprobacion ni saltarse verificacion.

SCREEN_ID: B-02_BUSINESS_VERIFICATION_FORM
actor: business applicant (non-persistent)
slice: business_intake_bot/admin_web
status: DRAFT_CONTROLLED

purpose:
Collect business verification data.

route:
/business/verify

entry points:
Onboarding

exit points:
B-03_VERIFICATION_PENDING

data required:
- authenticated user/session
- data defined by API contract for this screen
- private verification document metadata stored in `file_assets`

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
Enviar solicitud

validation:
required business data and private verification documents:
- business_name
- rif
- address
- phone
- country
- at least the required document set from API/security contract

permissions:
business applicant

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
business_registered
verification_document_uploaded

document rules:
- Uploads are included in slice_02.
- Documents must be private.
- Show only file metadata after upload.
- Never show storage paths or permanent public URLs.
- Use signed URLs only for authorized admin review.

QA checklist:
Uploads private; no storage_path exposed; missing document blocks submit
