# B-09_MY_ADS.md

SCREEN_ID: B-09_MY_ADS
actor: business
slice: business_app
status: DRAFT_CONTROLLED

purpose:
List active/paused/in_order ads.

route:
/business/ads

entry points:
Dashboard

exit points:
B-08_CREATE_AD, B-10_ARCHIVED_ADS

data required:
- authenticated user/session
- own business id
- paginated own operational ads from GET /api/v1/business/ads
- capabilities per ad: can_update, can_pause, can_archive, can_reactivate

endpoint used:
- GET /api/v1/business/ads
- PUT /api/v1/business/ads/{id}
- POST /api/v1/business/ads/{id}/pause
- POST /api/v1/business/ads/{id}/archive

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
Crear anuncio

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
- Show own ads only.
- Do not show private account_value in list.
- No fake counts or fake active ads.

audit events:
ad_updated, ad_paused, ad_archived when actions are executed

QA checklist:
No duplicates

## Slice 14B1 access contract

- Requires `surface/session` allowed for `business_mini_app`.
- Suspended business may view historical/current own ads only if backend capabilities include read-only ads.
- Blocked business or blocked/revoked link cannot operate ads.
