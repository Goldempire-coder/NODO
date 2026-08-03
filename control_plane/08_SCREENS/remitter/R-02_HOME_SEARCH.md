# R-02_HOME_SEARCH.md

SCREEN_ID: R-02_HOME_SEARCH
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
Enter amount and payment method to find compatible businesses.

route:
/home

entry points:
Welcome, bottom nav

exit points:
R-03_SEARCH_RESULTS, R-12_MY_ORDERS, R-13_PROFILE

data required:
- authenticated user/session
- amount_usd input
- payment_method segmented control: zelle|usdt_trc20
- delivery_method fixed to pago_movil_ve
- optional previous search state from local UI only

endpoint used:
- GET /api/v1/ads/search after local validation

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
- Use controlled home entry motion from MOTION_AND_INTERACTION.md.
- Respect reduced motion.

motion:
- header enters first
- amount card enters second
- recent orders and marketplace summary enter staggered
- CTA has press feedback
- no fake data animation

MainButton behavior:
Buscar negocios; disabled if invalid

validation:
amount >=20 <=2000; method zelle/usdt_trc20

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
Compara perfiles registrados en NODO segun tasa, limites y disponibilidad. Cada negocio publica sus propias condiciones.

privacy:
- Do not show private business payment account values.
- Do not show fake marketplace metrics.
- Do not show city/cash/nearest filters.

audit events:
search_started optional

QA checklist:
No city; no cash; sends usdt_trc20 not usdt
