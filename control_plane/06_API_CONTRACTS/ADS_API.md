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
    "rating_avg": "4.80|null",
    "completed_orders_count": 12,
    "reputation": {
      "tier": "new|active|reliable|elite",
      "label": "Nuevo|Activo|Confiable|Elite",
      "rating_avg": "4.80|null",
      "ratings_count": 11,
      "completed_orders_count": 12,
      "success_rate": "96.50|null",
      "average_delivery_seconds": 540
    }
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

Reglas de privacidad del objeto publico:

- Nunca incluye `risk_level`, `trust_level`, fallos atribuibles, disputas
  perdidas ni senales antifraude.
- `rating_avg` y `completed_orders_count` en el nivel de `business` se conservan
  como aliases publicos de compatibilidad para consumidores v1. Nuevos
  consumidores deben usar `business.reputation`.
- Una restriccion o revision interna se representa como indisponibilidad segura;
  no se devuelve `under_review` al cliente.
- El frontend presenta las metricas recibidas y no calcula tier, success rate ni
  promedios.

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
- Slice 42A no cambia el algoritmo de ranking. El token v1 `sort=trust`
  conserva temporalmente la heuristica interna existente y no expone
  `trust_level` en el DTO.
- El ranking reputacional objetivo debe ser implementado y medido en un slice
  posterior antes de sustituir esa heuristica:
  1. compatibilidad exacta de monto/metodo
  2. mayor `reputation_tier` calculado por backend
  3. mejor `rating_avg`
  4. mas `completed_orders_count`
  5. menor riesgo aplicado solo como control backend
  6. mejor tasa
- La mejor tasa no debe superar senales de riesgo.
- Las senales de riesgo se aplican solo como filtro backend; nunca salen en la
  respuesta publica.
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
- Si `status = active` pero `expires_at <= now()`, el servicio debe materializar `archived`, auditar `ad_expired`, consumir el hold con ledger `expire` cuando exista, y responder `AD_NOT_AVAILABLE`.
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
- El negocio debe tener PIN operativo configurado y desbloqueado; si no, backend responde `BUSINESS_PIN_NOT_SET`, `BUSINESS_PIN_REQUIRED` o `BUSINESS_PIN_LOCKED`.

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
- `amount_min_usd >= business.min_order_amount_usd`.
- `amount_max_usd >= amount_min_usd`.
- `amount_max_usd <= 2000`.
- `amount_max_usd <= business.max_order_amount_usd`.
- La suma de `amount_max_usd` de anuncios propios abiertos (`active`, `in_order`) mas el nuevo anuncio no puede superar `business.daily_limit_usd`.
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
- AD_LIMIT_NOT_ALLOWED
- BUSINESS_DAILY_LIMIT_EXCEEDED
- AD_OVERLAP_NOT_ALLOWED
- INVALID_PAYMENT_METHOD
- INVALID_DELIVERY_METHOD
- PAYMENT_METHOD_NOT_APPROVED
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH

## POST /api/v1/business/ads/{id}/republish

Republica un anuncio propio archivado o vencido como una nueva publicacion activa.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Volver a publicar"
}
```

Response 200:

```json
{
  "data": {
    "ad": {},
    "republished_from_ad_id": "ad_...",
    "credit_hold": {
      "ledger_id": "ledger_...",
      "required_credits": 1
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Owner-only.
- Solo permitido desde `archived` o `expired`.
- No reactiva el mismo registro: crea un anuncio nuevo con `status = active`, `activated_at = now()` y `expires_at = now() + 7 days`.
- Debe validar negocio publicable, metodo de pago aprobado, no solapamiento y creditos disponibles antes de publicar.
- Debe respetar `business.daily_limit_usd` sumando exposicion abierta existente y el anuncio nuevo.
- Si no hay creditos disponibles, no crea anuncio nuevo y responde `CREDIT_BALANCE_INSUFFICIENT`.
- La republicacion bloquea nuevos creditos con ledger `hold`.
- Auditar `ad_created`, `ad_published`, `credits_held` y `ad_republished`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- AD_NOT_FOUND
- AD_STATUS_INVALID
- PAYMENT_METHOD_NOT_APPROVED
- AD_OVERLAP_NOT_ALLOWED
- BUSINESS_DAILY_LIMIT_EXCEEDED
- CREDIT_BALANCE_INSUFFICIENT
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
- Si encuentra `active`/`paused` vencidos, puede materializar `archived` y consumir el hold con ledger `expire` antes de responder.
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
- Si el anuncio esta abierto (`active`, `in_order`), el nuevo `amount_max_usd` debe mantener la exposicion total dentro de `business.daily_limit_usd`.
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
- BUSINESS_DAILY_LIMIT_EXCEEDED
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
- Si `active`/`paused` vencio, primero materializa `archived` con audit `ad_expired` y ledger `expire` cuando exista.
- No libera creditos si el anuncio esta `in_order`; ese flujo pertenece a ordenes.
- Si el anuncio expiro sin pago confirmado, el credit service debe consumir el hold y registrar ledger `expire`.
- Auditar `ad_archived`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- AD_NOT_FOUND
- AD_STATUS_INVALID
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH
