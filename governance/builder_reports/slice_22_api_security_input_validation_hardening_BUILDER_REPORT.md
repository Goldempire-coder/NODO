# slice_22_api_security_input_validation_hardening BUILDER_REPORT

## Estado final

API READY WITH LIMITS

No se hizo deploy y no se declara READY_FOR_REAL_USE.

## Auditoria realizada

Se inventariaron 91 rutas reales `/api/v1` desde la app FastAPI. La auditoria se centro en entradas JSON/body, query models existentes, webhooks Telegram y endpoints Tier 0 con mutaciones sensibles.

Superficies revisadas:
- Auth, refresh, logout y users/me.
- Surface session.
- Marketplace y business ads.
- Orders remitter/business, payment report/evidence y chat.
- Businesses legacy/admin/access links/payment methods.
- Credits, referrals, Base USDC topups y admin credit review.
- Support cliente/negocio/admin.
- Staff admin.
- Admin users/businesses/orders/disputes/audit/jobs.
- Business intake API y Telegram webhook.
- Client Telegram webhook.
- Uploads privados por business verification, payment evidence, chat, support, credit proofs e intake.

## Problemas encontrados

### HIGH - campos extra aceptados silenciosamente

Los modelos Pydantic de request heredaban `BaseModel` sin `extra="forbid"`. En Pydantic v2 eso ignora campos no contratados por defecto.

Riesgo:
- Cliente podia enviar `business_id`, campos admin, flags o metadata arbitraria sin rechazo explicito.
- En payloads anidados, campos privados de almacenamiento podian llegar hasta validacion de schema sin ser rechazados por Pydantic.
- La API no cumplia la regla de no aceptar objetos arbitrarios ni campos extra.

Fix:
- Se creo `StrictRequestModel` con `extra="forbid"` y `str_strip_whitespace=True`.
- Se migraron los request/query/nested input models de los modulos API principales a `StrictRequestModel`.

### MEDIUM - limites incompletos en algunos strings/listas

Algunas entradas tenian `str` o listas sin maximo explicito.

Fix:
- Se agregaron limites a cursores, payment method input, business intake lists, staff permission fields y support scope/category/visibility.
- No se cambiaron enums ni reglas de negocio.

### MEDIUM - webhooks podian recibir JSON malformado/no objeto

`request.json()` en webhooks Telegram podia fallar antes del parser seguro o recibir un JSON no objeto.

Fix:
- Client bot webhook devuelve `VALIDATION_ERROR` seguro.
- Business intake bot webhook devuelve `BOT_INPUT_INVALID` seguro.
- No se imprimen tokens ni payloads sensibles.

## Cambios implementados

- Nuevo helper comun:
  - `apps/api/app/shared/validation.py`
- Schemas endurecidos:
  - `apps/api/app/modules/ads/schemas.py`
  - `apps/api/app/modules/orders/schemas.py`
  - `apps/api/app/modules/businesses/schemas.py`
  - `apps/api/app/modules/credits/schemas.py`
  - `apps/api/app/modules/chat/schemas.py`
  - `apps/api/app/modules/support/schemas.py`
  - `apps/api/app/modules/staff/schemas.py`
  - `apps/api/app/modules/business_intake/schemas.py`
  - `apps/api/app/modules/disputes/schemas.py`
  - `apps/api/app/modules/users/schemas.py`
- Admin route body model:
  - `apps/api/app/modules/admin/routes.py`
- Webhook input handling:
  - `apps/api/app/routes/telegram_bot.py`
  - `apps/api/app/modules/business_intake/telegram_routes.py`
- Tests:
  - `apps/api/tests/test_api_input_validation_hardening.py`
  - `apps/api/tests/test_business_verification.py`

## Inventario API auditado

Endpoint groups:
- Health/version/readiness: 3.
- Auth/users/surface: 7.
- Businesses public/legacy/admin/access/payment methods: 17.
- Business intake API/webhook/admin: 10.
- Ads marketplace/business: 7.
- Orders remitter/business/payment: 12.
- Chat: 3.
- Support client/admin/attachments: 13.
- Staff admin: 7.
- Credits/referrals/webhook/admin: 13.
- Disputes: 4.
- Admin console read/mutate routes: 16.
- Jobs admin: 3.
- Client Telegram webhook: 1.

Total real `/api/v1` routes enumerated from FastAPI: 91.

## Tests agregados

`apps/api/tests/test_api_input_validation_hardening.py` cubre:
- Auth/refresh rechazan campos extra con error seguro.
- Receiver data anidado de order creation rechaza campos extra.
- Support ticket y staff permission nested input rechazan campos extra.
- Admin reason whitespace-only conserva error canonico y no muta usuario.
- Telegram webhooks rechazan JSON malformado o no objeto sin stack trace.

Se actualizo `test_business_verification.py` para separar:
- IDOR/ownership con payload valido.
- rechazo de campos admin extra con `VALIDATION_ERROR`.

## Validacion ejecutada

- `python -m pytest apps\api\tests -q`
  - Resultado: `206 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: OK
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK
  - Next.js compiled/exported successfully.

## Scans

- Frontend source/build prohibited-string scan:
  - Resultado: 0 hits.
- Modified backend/test scan:
  - Encontradas referencias esperadas a nombres de variables/configuracion, storage internamente privado y strings de prueba.
  - No se detecto exposicion nueva en frontend build ni respuestas de error de tests.
- Strict request scan:
  - No quedan request models heredando `BaseModel`; solo response models publicos permanecen con `BaseModel`.

## Riesgos pendientes

- Este slice endurece schemas y webhooks, pero no reemplaza una campana completa de fuzzing automatizado por endpoint.
- Uploads multipart siguen validados en servicios especificos; no se introdujo framework nuevo de validacion de multipart.
- Algunos queries admin siguen definidos como parametros FastAPI individuales; mantienen limites actuales pero no se refactorizaron a query objects.
- El veredicto no es "API READY FOR PRODUCTION" porque no se ejecuto fuzzing exhaustivo externo ni staging/security DAST real.

## Que NO toque

- No cambie reglas de negocio.
- No cambie lifecycles de ordenes, creditos, ads, soporte, negocios, staff, bots o pagos.
- No relaje auth, RBAC, idempotencia ni ownership.
- No toque frontend de producto.
- No cree migraciones.
- No instale dependencias.
- No hice deploy.
- No declare READY_FOR_REAL_USE.
