# ADS_API.md

Contrato canonico de anuncios y marketplace para `slice_03_ads_marketplace`.

Todas las rutas usan prefijo:

```txt
/api/v1
```

## Reglas generales

- Backend valida auth, RBAC, ownership, estado actual, rate limit, idempotencia y audit cuando aplique.
- El frontend no decide permisos ni transiciones.
- `ad.status` solo puede ser: `draft`, `active`, `in_order`, `paused`, `expired`, `archived`, `suspended`.
- Marketplace solo muestra anuncios efectivos `active`, no vencidos, de negocios `approved`, no suspendidos/bloqueados.
- Click, search y detalle no consumen creditos.
- Crear orden no consume credito adicional; la orden queda para `slice_04_order_creation`.
- Publicar anuncio bloquea creditos por `amount_max_usd`.
- `active` dura 7 dias desde `activated_at`.
- Pausar no extiende `expires_at`.
- Expiracion masiva por worker queda para `slice_10_jobs_notifications`; slice 03 implementa expiracion pasiva/materializada.
- Responses usan `ERROR_CONTRACT.md`.

## Costos por rango

```txt
$20-$100 = 1 credito
$100-$500 = 2 creditos
$500-$2,000 = 3 creditos
> $2,000 = no disponible en MVP / revision manual futura
```

`required_credits` se calcula desde `amount_max_usd`.

## Objeto publico de anuncio

No expone datos privados completos del negocio ni instrucciones completas de pago.

```json
{
  "id": "uuid",
  "business": {
    "id": "uuid",
    "business_name": "Casa Cambio Centro",
    "verification_status": "approved",
    "trust_level": "new|basic|plus|pro|premium",
    "risk_level": "normal|watch|under_review|restricted|high_risk",
    "rating_avg": "4.80|null",
    "completed_orders_count": 12
  },
  "payment_method": "zelle|usdt_trc20",
  "delivery_method": "pago_movil_ve",
  "rate_bs_per_usd": "36.5000",
  "amount_min_usd": "20.00",
  "amount_max_usd": "100.00",
  "required_credits": 1,
  "status": "active",
  "effective_status": "active|expired",
  "expires_at": "timestamp",
  "capabilities": {
    "can_create_order": true
  }
}
```

## Objeto de anuncio propio

Puede incluir campos operativos del negocio, pero no expone datos completos de metodo de pago salvo lo necesario para el owner.

```json
{
  "id": "uuid",
  "business_id": "uuid",
  "payment_method_id": "uuid",
  "payment_method": "zelle|usdt_trc20",
  "delivery_method": "pago_movil_ve",
  "rate_bs_per_usd": "36.5000",
  "amount_min_usd": "20.00",
  "amount_max_usd": "100.00",
  "required_credits": 1,
  "status": "draft|active|in_order|paused|expired|archived|suspended",
  "effective_status": "draft|active|in_order|paused|expired|archived|suspended",
  "activated_at": "timestamp|null",
  "expires_at": "timestamp|null",
  "rate_updated_at": "timestamp|null",
  "capabilities": {
    "can_update": true,
    "can_pause": true,
    "can_archive": false,
    "can_reactivate": false
  },
  "created_at": "timestamp"
}
```

## GET /api/v1/ads/search

Busca anuncios compatibles para remitentes.

Auth:

- `Authorization: Bearer <session_jwt>`
- Actor: `remitter` activo/restricted segun auth policy.

Query:

```txt
amount_usd=20..2000
payment_method=zelle|usdt_trc20
delivery_method=pago_movil_ve
cursor=opaque|null
limit=1..50
sort=trust|rate|speed|null
```

Response 200:

```json
{
  "data": {
    "items": [],
    "next_cursor": "opaque|null",
    "capabilities": {
      "can_create_order": false
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Cursor pagination obligatorio.
- Sin offset en tablas calientes.
- Filtra por:
  - `ads.status = active`
  - `ads.expires_at > now()`
  - `business.verification_status = approved`
  - `business.risk_level not in ('restricted', 'high_risk')`
  - rango compatible: `amount_min_usd <= amount_usd <= amount_max_usd`
  - metodo compatible.
- Ranking:
  1. compatibilidad exacta de monto/metodo
  2. mayor `trust_level`
  3. mejor `rating_avg`
  4. mas `completed_orders_count`
  5. menor `evasion_reports_count`/riesgo
  6. mejor tasa
- La mejor tasa no debe superar senales de riesgo.
- Rate limit por IP, user, route y metodo/monto.
- Audit: no obligatorio; `search_started` opcional y no debe saturar audit logs.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- VALIDATION_ERROR
- INVALID_PAYMENT_METHOD
- INVALID_DELIVERY_METHOD
- RATE_LIMITED

## GET /api/v1/ads/{id}

Detalle publico de anuncio activo.

Auth:

- `Authorization: Bearer <session_jwt>`
- Actor: `remitter` activo/restricted.

Response 200:

```json
{
  "data": {
    "ad": {},
    "disclaimer": "Negocio verificado por NODO. La operacion final es entre usuario y negocio."
  },
  "request_id": "req_..."
}
```

Rules:

- No expone `account_value`, instrucciones completas, storage paths, documentos ni datos privados.
- Si `status = active` pero `expires_at <= now()`, el servicio debe materializar `expired`, auditar `ad_expired` y responder `AD_NOT_AVAILABLE` o devolver `effective_status = expired` segun politica de detalle.
- Detalle/click no consume creditos.
- Rate limit por user/IP/ad.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- AD_NOT_FOUND
- AD_NOT_AVAILABLE
- RATE_LIMITED

## POST /api/v1/business/ads

Crea y publica un anuncio activo. En este MVP no se expone borrador persistente desde UI; `draft` queda reservado para flujos internos/futuros antes de publicar.

Precondicion UI/API:

- La Mini App Negocio debe cargar opciones desde `GET /api/v1/business/payment-methods`.
- La UI debe mostrar un selector visual de metodos aprobados; queda prohibido pedir al usuario escribir un `payment_method_id`.
- `payment_method_id` sigue siendo obligatorio en el request, pero debe venir de una opcion aprobada por backend.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "business_id": "uuid",
  "payment_method_id": "uuid",
  "payment_method": "zelle",
  "delivery_method": "pago_movil_ve",
  "rate_bs_per_usd": "36.5000",
  "amount_min_usd": "20.00",
  "amount_max_usd": "100.00"
}
```

Response 201:

```json
{
  "data": {
    "ad": {},
    "credit_hold": {
      "ledger_id": "uuid",
      "required_credits": 1
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Actor: `business_owner`.
- Owner solo crea para su propio negocio.
- Business debe estar `approved`.
- Business no puede estar `suspended`/`blocked`/risk `high_risk`.
- `payment_method_id` debe pertenecer al negocio y estar `verified_status = approved` y `active = true`.
- `payment_method` debe coincidir con el metodo registrado.
- `delivery_method = pago_movil_ve`.
- `amount_min_usd >= 20`.
- `amount_max_usd >= amount_min_usd`.
- `amount_max_usd <= 2000`.
- `amount_max_usd <= business.max_order_amount_usd`.
- No permite rangos solapados activos para misma combinacion metodo/entrega.
- Si `credit_wallet` no existe, slice 03 lo crea de forma idempotente con balances cero antes de validar saldo/founder.
- Si founder access activo y no expirado, puede publicar sin descontar creditos, pero debe registrar ledger `founder_free_use` o metadata de exencion segun credit service.
- Si no hay founder access, publicar hace hold transaccional:
  - resta `available_credits`
  - suma `blocked_credits`
  - crea `credits_ledger.type = hold`
  - setea `ads.credit_hold_ledger_id`
- `status = active`, `activated_at = now()`, `expires_at = activated_at + 7 days`.
- Auditar `ad_created`, `ad_published`, `credits_held` cuando aplica hold real.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- BUSINESS_NOT_APPROVED
- BUSINESS_NOT_FOUND
- CREDIT_WALLET_NOT_FOUND
- CREDIT_BALANCE_INSUFFICIENT
- AD_AMOUNT_RANGE_INVALID
- AD_AMOUNT_TOO_HIGH
- AD_OVERLAP_NOT_ALLOWED
- INVALID_PAYMENT_METHOD
- INVALID_DELIVERY_METHOD
- PAYMENT_METHOD_NOT_APPROVED
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH

## GET /api/v1/business/ads

Lista anuncios propios operativos para B-09.

Auth:

- `business_owner`, negocio propio.

Query:

```txt
business_id=uuid
status=active|paused|in_order|suspended|null
cursor=opaque|null
limit=1..50
```

Response 200:

```json
{
  "data": {
    "items": [],
    "next_cursor": "opaque|null"
  },
  "request_id": "req_..."
}
```

Rules:

- Solo anuncios del negocio propio.
- Por defecto excluye `archived` y `expired`.
- Si encuentra `active`/`paused` vencidos, puede materializar `expired` antes de responder.
- Cursor pagination.
- No audit requerido para lectura.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- BUSINESS_NOT_FOUND
- RATE_LIMITED

## GET /api/v1/business/ads/archived

Lista historica para B-10.

Auth:

- `business_owner`, negocio propio.

Query:

```txt
business_id=uuid
cursor=opaque|null
limit=1..50
```

Response 200:

```json
{
  "data": {
    "items": [],
    "next_cursor": "opaque|null"
  },
  "request_id": "req_..."
}
```

Rules:

- Solo anuncios propios con `status in ('archived', 'expired')`.
- Cursor pagination.
- Historical only; no mutacion desde lista.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- BUSINESS_NOT_FOUND
- RATE_LIMITED

## PUT /api/v1/business/ads/{id}

Actualiza campos editables de anuncio propio.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "rate_bs_per_usd": "36.5000",
  "amount_min_usd": "20.00",
  "amount_max_usd": "100.00"
}
```

Response 200:

```json
{
  "data": {
    "ad": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Owner-only.
- Permitido para `active` o `paused` no vencidos.
- No permite modificar `business_id`, `payment_method_id`, `payment_method`, `delivery_method`, `status`, `credit_hold_ledger_id`.
- Si cambia `amount_max_usd` y cambia `required_credits`, debe revalidar saldo y ajustar hold de forma transaccional; si esa operacion no esta implementada, el backend debe rechazar con `AD_STATUS_INVALID` o `CREDIT_BALANCE_INSUFFICIENT`, no mutar parcial.
- Actualizar rate setea `rate_updated_at`.
- Auditar `ad_updated`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- AD_NOT_FOUND
- AD_STATUS_INVALID
- AD_AMOUNT_RANGE_INVALID
- AD_AMOUNT_TOO_HIGH
- AD_OVERLAP_NOT_ALLOWED
- CREDIT_BALANCE_INSUFFICIENT
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH

## POST /api/v1/business/ads/{id}/pause

Pausa anuncio propio activo.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Pausa temporal"
}
```

Response 200:

```json
{
  "data": {
    "ad": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Owner-only.
- Solo `active` no vencido.
- Pausar no cambia `expires_at` ni libera creditos.
- Auditar `ad_paused`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- AD_NOT_FOUND
- AD_STATUS_INVALID
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH

## POST /api/v1/business/ads/{id}/archive

Archiva anuncio propio pausado o expirado.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Cierre operativo"
}
```

Response 200:

```json
{
  "data": {
    "ad": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Owner-only.
- Permitido desde `paused` o `expired`.
- Si `active`/`paused` vencio, primero materializa `expired` con audit `ad_expired`; luego puede archivar.
- No libera creditos si el anuncio esta `in_order`; ese flujo pertenece a ordenes.
- Si el anuncio expiro sin orden/pago confirmado, el credit service debe liberar hold y registrar ledger `release`. Si release no esta disponible en slice 03, archivar debe bloquear con `AD_STATUS_INVALID` y reportar bloqueo antes de construir.
- Auditar `ad_archived`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- AD_NOT_FOUND
- AD_STATUS_INVALID
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH
