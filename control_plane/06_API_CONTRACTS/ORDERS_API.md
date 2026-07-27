# ORDERS_API.md

Contrato canonico de ordenes para `slice_04_order_creation`.

Las operaciones del negocio sobre ordenes despues de reporte de pago quedan gobernadas por:

```txt
control_plane/06_API_CONTRACTS/BUSINESS_ORDERS_API.md
```

Todas las rutas usan prefijo:

```txt
/api/v1
```

Quedan prohibidas las rutas legacy sin prefijo como `POST /orders`, `GET /orders/:id`, `POST /orders/:id/extend` o `POST /orders/:id/cancel`.

## Reglas generales

- Backend valida auth, RBAC, ownership, estado actual, rate limit, idempotencia y audit.
- El frontend no decide permisos ni transiciones.
- Crear orden no consume creditos.
- Crear orden no cobra al usuario.
- Crear orden no reporta pago.
- Crear orden no confirma pago del negocio.
- Crear orden no entrega pago movil.
- Crear orden no abre chat ni disputa.
- Crear orden mueve el anuncio `active -> in_order`.
- Una orden creada por `POST /api/v1/orders` persiste directamente como `waiting_payment`.
- `created` puede registrarse solo como evento/audit/state event de creacion; no es el estado persistente final del endpoint.
- La expiracion masiva queda para `slice_10_jobs_notifications`; slice 04 define expiracion pasiva/materializada al leer o mutar una orden `waiting_payment` vencida.
- Responses usan `ERROR_CONTRACT.md`.

## Objeto publico/resumido de orden

No expone instrucciones completas de pago, `account_value`, storage paths, documentos ni datos privados del negocio.

```json
{
  "id": "uuid",
  "public_order_code": "NODO-ABC123",
  "ad_id": "uuid",
  "business_id": "uuid",
  "business_name": "Casa Cambio Centro",
  "status": "waiting_payment|cancelled",
  "amount_usd": "50.00",
  "rate_snapshot": "36.500000",
  "amount_bs_calculated": "1825.00",
  "payment_method_snapshot": "zelle|usdt_trc20",
  "delivery_method_snapshot": "pago_movil_ve",
  "payment_instructions_masked": {
    "method": "zelle",
    "account_masked": "ca***@domain.com"
  },
  "payment_report_deadline_at": "timestamp",
  "payment_report_extension_used_at": "timestamp|null",
  "extension_used": false,
  "expires_at": "timestamp",
  "cancel_reason": "payment_not_reported_in_time|remitter_cancelled_before_payment|null",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "capabilities": {
    "can_extend_payment_deadline": true,
    "can_cancel": true,
    "can_view_payment_instructions": false
  }
}
```

## Snapshot privado de instrucciones

Slice 04 puede guardar `payment_instructions_snapshot` de forma privada al crear la orden para congelar la instruccion usada.

Slice 04 no debe revelar instrucciones completas en create/detail/list.

Slice 05 revela instrucciones completas mediante:

```txt
GET /api/v1/orders/{id}/payment-instructions
```

Slice 05 debe setear `payment_data_revealed_at` y `payment_data_revealed_by` al revelar instrucciones, auditar `payment_instructions_viewed` y no crear reporte de pago desde este endpoint.

## POST /api/v1/orders

Crea una orden desde un anuncio activo.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "ad_id": "uuid",
  "amount_usd": "50.00",
  "receiver_data": {
    "bank": "Banco",
    "phone": "+584121234567",
    "document": "V12345678",
    "holder": "Nombre Receptor"
  }
}
```

Response 201:

```json
{
  "data": {
    "order": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Actor: `remitter` activo.
- `Idempotency-Key` obligatorio.
- Validar anuncio `active`, no vencido y disponible.
- Si el anuncio vencio, materializar expiracion y responder `AD_EXPIRED` o `AD_NOT_AVAILABLE`.
- Validar negocio `approved` y no `restricted/high_risk`.
- Validar `amount_usd >= 20`.
- Validar `amount_min_usd <= amount_usd <= amount_max_usd`.
- Validar limites del negocio, incluyendo `business.max_order_amount_usd` y `active_order_limit` cuando aplique.
- `active_order_limit` cuenta obligaciones abiertas: `waiting_payment`,
  `payment_reported`, `payment_rejected`, `payment_confirmed`, `delivered` y
  `disputed`.
- Validar capacidad efectiva y limite diario restante contra `amount_usd`.
- Crear una reserva unica ligada a `order_id` dentro de la misma transaccion
  que crea la orden.
- Crear orden persistida como `waiting_payment`.
- Guardar snapshot inmutable de tasa, monto, negocio, metodo, delivery, limites usados e instrucciones privadas.
- Calcular `amount_bs_calculated = amount_usd * rate_snapshot`.
- Setear `payment_report_deadline_at = now() + 30 minutes`.
- Setear `expires_at = payment_report_deadline_at`.
- Setear `extension_used = false`.
- Mover anuncio `active -> in_order`.
- Crear `order_state_events`.
- Auditar `order_created`, `ad_moved_in_order` y
  `business_capacity_reserved`.
- Retry con misma idempotency key y mismo payload debe devolver la misma orden.
- Retry con misma idempotency key y payload distinto debe devolver `IDEMPOTENCY_CONFLICT`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- IDEMPOTENCY_PAYLOAD_MISMATCH
- AD_NOT_FOUND
- AD_NOT_AVAILABLE
- AD_EXPIRED
- BUSINESS_NOT_APPROVED
- AMOUNT_OUT_OF_RANGE
- ORDER_ALREADY_EXISTS
- BUSINESS_CAPACITY_INSUFFICIENT
- BUSINESS_CAPACITY_RESERVATION_CONFLICT
- RATE_LIMITED

## POST /api/v1/orders/{id}/rating

Crea una calificacion de 1 a 5 estrellas para una orden propia `completed`.
El contrato completo vive en el `API_CONTRACT.md` del slice 42B.

Rules:

- solo el cliente propietario activo;
- `Idempotency-Key` obligatorio;
- una calificacion por orden;
- una disputa debe estar cerrada;
- sin comentarios ni campos extra;
- insercion y recalculo de reputacion ocurren en una sola operacion segura;
- la respuesta publica no expone controles internos.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- ORDER_NOT_FOUND
- RATING_NOT_ALLOWED
- RATING_ALREADY_EXISTS
- VALIDATION_ERROR

## GET /api/v1/orders/{id}

Detalle resumido de orden propia.

Auth:

- `Authorization: Bearer <session_jwt>`
- Actor: remitente owner de la orden. Business owner/support/admin reads quedan para slices posteriores salvo contrato explicito.
- Lecturas de negocio usan `GET /api/v1/business/orders` y `GET /api/v1/business/orders/{id}` segun `BUSINESS_ORDERS_API.md`.

Response 200:

```json
{
  "data": {
    "order": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Solo remitente propietario puede ver la orden en slice 04.
- Si la orden `waiting_payment` vencio, el servicio debe materializar cancelacion por `payment_not_reported_in_time` antes de responder.
- No revela instrucciones completas; solo masked/resumen.
- No revela `account_value`, documentos, storage paths ni datos internos.
- Rate limit por user/IP/order.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- RATE_LIMITED

## GET /api/v1/orders/mine

Lista ordenes propias del remitente.

Auth:

- `Authorization: Bearer <session_jwt>`

Query:

```txt
status=waiting_payment|cancelled|null
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

- Solo ordenes propias.
- Cursor pagination obligatorio.
- No offset en tablas calientes.
- Puede materializar expiracion pasiva de ordenes `waiting_payment` vencidas antes de responder.
- No revela instrucciones completas.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- RATE_LIMITED

## POST /api/v1/orders/{id}/extend-payment-deadline

Extiende una sola vez el deadline de reporte de pago.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Necesito unos minutos mas"
}
```

Response 200:

```json
{
  "data": {
    "order": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Solo remitente propietario.
- Solo `waiting_payment`.
- Solo si `extension_used = false`.
- Si la orden ya vencio, primero materializar cancelacion por vencimiento y responder `ORDER_EXPIRED` o `ORDER_STATUS_INVALID`.
- Agrega 15 minutos.
- Setea `extension_used = true`.
- Setea `payment_report_extension_used_at`.
- Actualiza `payment_report_deadline_at` y `expires_at`.
- Crea state event.
- Audita `payment_deadline_extended`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_EXPIRED
- ORDER_STATUS_INVALID
- ORDER_EXTENSION_ALREADY_USED
- ORDER_PAYMENT_ALREADY_REPORTED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- RATE_LIMITED

## POST /api/v1/orders/{id}/cancel

Cancela una orden propia antes de reportar pago.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "No pude realizar el pago"
}
```

Response 200:

```json
{
  "data": {
    "order": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Solo remitente propietario.
- Solo `waiting_payment` antes de `payment_reported`.
- Setea `order.status = cancelled`.
- Setea `cancel_reason = remitter_cancelled_before_payment`.
- Si el anuncio no vencio: `ad.status = active` y el credito permanece bloqueado para la publicacion.
- Si el anuncio vencio: materializar `ad.status = archived` y consumir el hold con ledger `expire`.
- Crear state event.
- Liberar la reserva de capacidad una sola vez.
- Auditar `order_cancelled` y `business_capacity_released`.
- No reporta pago ni toca evidencia.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- ORDER_PAYMENT_ALREADY_REPORTED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- RATE_LIMITED

## Lifecycle de capacidad

- `waiting_payment`, `payment_reported`, `payment_rejected`,
  `payment_confirmed`, `delivered` y `disputed` conservan la reserva.
- Cancelacion o expiracion libera la reserva una sola vez.
- `completed` consume la reserva una sola vez y reduce la capacidad declarada;
  el monto consumido no reaparece automaticamente como disponible.
- Resolver una disputa aplica la accion terminal resultante: `completed`
  consume y `cancelled` libera.
- El replay de una transicion no duplica reserva, liberacion ni consumo.
