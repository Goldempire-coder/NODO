# BUSINESS_ORDERS_API.md

Contrato canonico para operaciones del negocio sobre ordenes en `slice_06_business_order_ops`.

Todas las rutas usan prefijo `/api/v1`.

## Endpoints

- `GET /api/v1/business/orders`
- `GET /api/v1/business/orders/{id}`
- `POST /api/v1/business/orders/{id}/confirm-payment`
- `POST /api/v1/business/orders/{id}/reject-payment-report`
- `POST /api/v1/business/orders/{id}/mark-delivered`

## Headers comunes

Lecturas:

```txt
Authorization: Bearer <session_jwt>
X-Request-Id: requerido o generado por backend
```

Mutaciones:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

## Ownership y RBAC

Todo endpoint de negocio debe:

- requerir auth JWT.
- requerir actor `business_owner` activo.
- cargar negocio aprobado del owner.
- operar solo ordenes cuyo `orders.business_id` pertenece al negocio del owner.
- no filtrar existencia de ordenes ajenas.
- no permitir `business_operator` en MVP.
- no permitir mutaciones de `admin` o `support` salvo contrato futuro explicito.
- aplicar rate limit backend.

## Objeto resumido de orden para negocio

No expone `storage_path`, tokens, secretos ni instrucciones completas innecesarias.

```json
{
  "id": "uuid",
  "public_order_code": "NODO-ABC123",
  "status": "payment_reported|payment_rejected|payment_confirmed|delivered|disputed",
  "amount_usd": "50.00",
  "amount_bs_calculated": "1825.00",
  "payment_method_snapshot": "zelle|usdt_trc20",
  "delivery_method_snapshot": "pago_movil_ve",
  "paid_reported_at": "timestamp|null",
  "payment_confirmed_at": "timestamp|null",
  "delivered_at": "timestamp|null",
  "business_response_warning_at": "timestamp|null",
  "business_response_deadline_at": "timestamp|null",
  "delivery_warning_at": "timestamp|null",
  "delivery_deadline_at": "timestamp|null",
  "auto_complete_at": "timestamp|null",
  "capabilities": {
    "can_confirm_payment": true,
    "can_reject_payment_report": true,
    "can_mark_delivered": false
  }
}
```

## GET /api/v1/business/orders

Lista solo ordenes del negocio propio.

Query:

```txt
status=payment_reported|payment_rejected|payment_confirmed|delivered|disputed|null
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

- Cursor pagination obligatorio.
- No offset en tablas calientes.
- No expone instrucciones completas.
- No expone `account_value`.
- No expone `storage_path`.
- Puede devolver capabilities calculadas por backend.

Errores:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `RATE_LIMITED`
- `VALIDATION_ERROR`

## GET /api/v1/business/orders/{id}

Detalle operativo de una orden del negocio.

Response 200:

```json
{
  "data": {
    "order": {},
    "payment_report": {
      "id": "uuid",
      "status": "submitted|accepted|rejected|corrected",
      "payment_type": "zelle|usdt_trc20",
      "payment_reference_masked": "***1234",
      "tx_hash": "full_tx_hash_if_needed_for_usdt_verification",
      "tx_hash_masked": "0xabc...789",
      "payment_amount": "50.00",
      "proof_file": {
        "id": "uuid",
        "file_type": "payment_evidence",
        "mime_type": "image/png",
        "size_bytes": 120000,
        "created_at": "timestamp"
      }
    },
    "receiver_data": {
      "bank": "Banco",
      "phone_masked": "+58*******123",
      "document_masked": "V***678",
      "holder": "Nombre Receptor"
    },
    "timeline": []
  },
  "request_id": "req_..."
}
```

Rules:

- Solo negocio dueno.
- Incluye `payment_report` submitted/accepted/rejected necesario para operar.
- Incluye metadata publica de evidencia, nunca `storage_path`.
- Puede mostrar `tx_hash` completo al negocio solo si es necesario para verificar USDT TRC20.
- Listados, audit y logs deben usar `tx_hash_masked`.
- No expone `account_value` del negocio si no es necesario para operar.
- Puede incluir timeline basico de `order_state_events`.

Errores:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `ORDER_NOT_FOUND`
- `ORDER_NOT_OWNED`
- `RATE_LIMITED`

## POST /api/v1/business/orders/{id}/confirm-payment

Confirma que el negocio recibio realmente el pago reportado.

Request:

```json
{
  "reason": "Pago recibido y verificado"
}
```

Response 200:

```json
{
  "data": {
    "order": {
      "id": "uuid",
      "status": "payment_confirmed",
      "payment_confirmed_at": "timestamp",
      "delivery_warning_at": "timestamp",
      "delivery_deadline_at": "timestamp"
    },
    "payment_report": {
      "id": "uuid",
      "status": "accepted"
    },
    "credit_ledger": {
      "type": "consume",
      "amount": 1,
      "related_order_id": "uuid"
    },
    "disclaimer": "Confirmar recepcion consume creditos del anuncio. Enviar pago movil es una accion separada."
  },
  "request_id": "req_..."
}
```

Rules:

- `Idempotency-Key` obligatorio.
- Solo negocio dueno.
- Requiere `orders.status = payment_reported`.
- Requiere `payment_reports.status = submitted` existente.
- Cambia `orders.status = payment_confirmed`.
- Setea `orders.payment_confirmed_at`.
- Setea `delivery_warning_at = now + 30 minutes`.
- Setea `delivery_deadline_at = now + 2 hours`.
- Actualiza `payment_reports.status = accepted`.
- Consume creditos bloqueados del anuncio:
  - `credit_wallets.blocked_credits -= ads.required_credits`
  - `credit_wallets.consumed_credits += ads.required_credits`
- Setea `ad.status = archived`.
- Crea `credits_ledger.type = consume`.
- Crea `order_state_events`.
- Audita `payment_confirmed`, `credits_consumed` y `ad_archived`.
- No marca `delivered`.
- No completa la orden.
- No abre disputa.
- La orden sigue viva para entrega, disputa o cierre futuro.
- El anuncio no vuelve al marketplace.

Ledger `consume`:

```txt
business_id = orders.business_id
type = consume
amount = ads.required_credits
related_ad_id = orders.ad_id
related_order_id = orders.id
reason = business_confirmed_payment_received
source = orders
reference_type = order
reference_id = orders.id
created_by = business owner id
```

Doble consumo:

- Misma key + mismo payload devuelve mismo resultado.
- Misma key + payload distinto devuelve `IDEMPOTENCY_PAYLOAD_MISMATCH` o `IDEMPOTENCY_CONFLICT`.
- Si ya existe ledger `consume` para `related_order_id/reference_id`, no consumir otra vez.
- Si no existe hold bloqueado valido, devolver `CREDIT_HOLD_NOT_FOUND`.
- Si un intento no idempotente detecta consumo previo, devolver `CREDIT_ALREADY_CONSUMED` u `ORDER_STATUS_INVALID` segun estado actual.
- La actualizacion de order, report, wallet y ledger debe ser transaccional.

Errores:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `ORDER_NOT_FOUND`
- `ORDER_NOT_OWNED`
- `ORDER_STATUS_INVALID`
- `PAYMENT_REPORT_NOT_FOUND`
- `PAYMENT_CONFIRMATION_NOT_ALLOWED`
- `CREDIT_HOLD_NOT_FOUND`
- `CREDIT_ALREADY_CONSUMED`
- `IDEMPOTENCY_KEY_REQUIRED`
- `IDEMPOTENCY_CONFLICT`
- `IDEMPOTENCY_PAYLOAD_MISMATCH`
- `RATE_LIMITED`
- `VALIDATION_ERROR`

## POST /api/v1/business/orders/{id}/reject-payment-report

Rechaza el reporte de pago del remitente.

Request:

```json
{
  "reason": "Referencia no encontrada en la cuenta"
}
```

Response 200:

```json
{
  "data": {
    "order": {
      "id": "uuid",
      "status": "payment_rejected"
    },
    "payment_report": {
      "id": "uuid",
      "status": "rejected"
    },
    "disclaimer": "Rechazar el reporte no libera automaticamente el anuncio ni los creditos. El caso queda con trazabilidad para correccion, soporte o disputa futura."
  },
  "request_id": "req_..."
}
```

Decision canonica:

```txt
payment_reported -> payment_rejected
```

No se devuelve automaticamente a `waiting_payment`.

Rules:

- `Idempotency-Key` obligatorio.
- Solo negocio dueno.
- Requiere `orders.status = payment_reported`.
- Requiere `payment_reports.status = submitted` existente.
- `reason` obligatorio.
- Cambia `orders.status = payment_rejected`.
- Cambia `payment_reports.status = rejected`.
- Crea `order_state_events`.
- Audita `payment_report_rejected`.
- No consume creditos.
- Creditos siguen bloqueados hasta resolucion, cancelacion o disputa futura.
- `ad.status` sigue `in_order`.
- No libera el anuncio.
- No devuelve orden al marketplace.

Errores:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `ORDER_NOT_FOUND`
- `ORDER_NOT_OWNED`
- `ORDER_STATUS_INVALID`
- `PAYMENT_REPORT_NOT_FOUND`
- `PAYMENT_REJECTION_NOT_ALLOWED`
- `ADMIN_REASON_REQUIRED`
- `IDEMPOTENCY_KEY_REQUIRED`
- `IDEMPOTENCY_CONFLICT`
- `IDEMPOTENCY_PAYLOAD_MISMATCH`
- `RATE_LIMITED`
- `VALIDATION_ERROR`

## POST /api/v1/business/orders/{id}/mark-delivered

Marca que el negocio envio el pago movil.

Request:

```json
{
  "reason": "Pago movil enviado"
}
```

Response 200:

```json
{
  "data": {
    "order": {
      "id": "uuid",
      "status": "delivered",
      "delivered_at": "timestamp",
      "auto_complete_warning_12h_at": "timestamp",
      "auto_complete_warning_23h_at": "timestamp",
      "auto_complete_at": "timestamp"
    },
    "disclaimer": "Marcar entregado no completa la orden. El remitente debe confirmar recibido o el cierre automatico queda para un slice futuro."
  },
  "request_id": "req_..."
}
```

Rules:

- `Idempotency-Key` obligatorio.
- Solo negocio dueno.
- Requiere `orders.status = payment_confirmed`.
- Cambia `orders.status = delivered`.
- Setea `orders.delivered_at`.
- Setea `auto_complete_warning_12h_at = now + 12 hours`.
- Setea `auto_complete_warning_23h_at = now + 23 hours`.
- Setea `auto_complete_at = now + 24 hours`.
- Crea `order_state_events`.
- Audita `order_delivered`.
- No completa la orden.
- No confirma recepcion del cliente.
- No abre chat/disputa.
- No consume creditos aqui.

Errores:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `ORDER_NOT_FOUND`
- `ORDER_NOT_OWNED`
- `ORDER_STATUS_INVALID`
- `DELIVERY_NOT_ALLOWED`
- `IDEMPOTENCY_KEY_REQUIRED`
- `IDEMPOTENCY_CONFLICT`
- `IDEMPOTENCY_PAYLOAD_MISMATCH`
- `RATE_LIMITED`
- `VALIDATION_ERROR`

## Sensitive data y masking

- `storage_path` nunca aparece en API publica, frontend, audit ni logs.
- `account_value` no aparece en list/detail de negocio salvo contrato futuro explicito.
- Full payment instructions solo pertenecen a `GET /api/v1/orders/{id}/payment-instructions` del remitente owner.
- `tx_hash` puede mostrarse completo al negocio en detail si es necesario para verificar USDT; listados, audit y logs usan version masked/truncated.
- Evidencia de pago se muestra como metadata publica o signed URL futura segun contrato de storage; nunca como path privado.

## Rate limits

Aplicar rate limit backend por:

- user id
- business id
- order id
- route/action
- IP cuando aplique

## Idempotencia

Para `confirm-payment`, `reject-payment-report` y `mark-delivered`:

- `Idempotency-Key` obligatorio.
- Misma key + mismo payload devuelve mismo resultado.
- Misma key + payload distinto devuelve `IDEMPOTENCY_PAYLOAD_MISMATCH` o `IDEMPOTENCY_CONFLICT`.
- No crear tabla nueva salvo contrato explicito futuro.
- Preferido: usar idempotency store existente para acciones mutantes.
- Confirm-payment tambien debe protegerse con ledger `consume` existente para evitar doble consumo aunque falle un retry.

## Scope prohibido en slice 06

- chat
- disputas
- confirmacion de recibido por remitente
- auto-complete
- jobs masivos
- admin override
- compra/acreditacion real de creditos
- B-13 business chat salvo link/estado hacia slice 07
- R-09 order tracking/chat
- R-10 confirm received
