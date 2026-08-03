# R-03_SEARCH_RESULTS.md

SCREEN_ID: R-03_SEARCH_RESULTS
actor: remitter
slice: remitter_app
status: DRAFT_CONTROLLED

purpose:
Show compatible verified businesses.

route:
/businesses

entry points:
Home search

exit points:
R-04_BUSINESS_DETAIL, R-02_HOME_SEARCH

data required:
- authenticated user/session
- search query: amount_usd, payment_method, delivery_method
- paginated ad results from GET /api/v1/ads/search
- next_cursor

endpoint used:
- GET /api/v1/ads/search

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
Seleccionar negocio

validation:
amount/method required

permissions:
remitter active

states:
- loading
- empty
- error
- offline
- forbidden
- success where applicable

filters:
- Mejor tasa

compatibility:
- La API conserva `sort=trust` y `sort=speed` para clientes anteriores, pero
  ambos usan el mismo orden por tasa/fecha que `sort=rate` mientras no exista
  snapshot publico durable.
- La UI no ofrece controles llamados `Mejor confianza` o `Mas rapido` cuando no
  puede respaldar esas promesas sin metricas vivas.

forbidden filters:
- Mas cercano
- Por ciudad
- Efectivo
- Retiro fisico

disclaimer:
Todos los negocios publicados pasan por verificacion basica de NODO. Revisa tasa, limites, disponibilidad e instrucciones antes de crear una orden.

privacy:
- Show only public ad object from ADS_API.
- Do not show full payment account values or private business documents.
- Do not hardcode active business counts, best rates or recent orders.

audit events:
none

QA checklist:
- No mostrar `Mas cercano`, `Mejor confianza` ni `Mas rapido`.
- Orden visible por mejor tasa sin reputacion viva.
