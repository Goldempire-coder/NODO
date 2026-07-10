# B-10_ARCHIVED_ADS.md

SCREEN_ID: B-10_ARCHIVED_ADS
actor: business
slice: business_app
status: DRAFT_CONTROLLED

purpose:
List archived ads.

route:
/business/ads/archived

entry points:
My Ads

exit points:
B-09_MY_ADS

data required:
- authenticated user/session
- own business id
- paginated archived/expired ads from GET /api/v1/business/ads/archived
- next_cursor

endpoint used:
- GET /api/v1/business/ads/archived

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
own ads

states:
- loading
- empty
- error
- offline
- forbidden
- success where applicable

disclaimer:
Los creditos son para publicar y operar anuncios dentro de NODO. No son saldo de clientes ni fondos de remesas.

privacy:
- Historical own ads only.
- Do not expose private account values.
- No fake historical metrics.

audit events:
none

QA checklist:
Historical only
