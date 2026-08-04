# ORDERS_API.md

Contrato canonico de ordenes para `slice_04_order_creation`.

Las operaciones del negocio sobre ordenes despues de reporte de pago quedan gobernadas por:

```txt
control_plane/06_API_CONTRACTS/BUSINESS_ORDERS_API.md
```

La reconciliacion final de completion, capacidad y payload seguro de receptor
queda gobernada por:

```txt
control_plane/09_SLICES/slice_50B_p2p_completion_contract_reconciliation/
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
- Crear orden habilita el chat privado inmediato para los dos participantes.
- Crear orden no abre disputa.
- Reportar pago no consume creditos.
- Solo la confirmacion oficial del negocio
  `payment_reported -> payment_confirmed` consume el credito publicitario.
- Completar la orden no consume credito otra vez; consume la capacidad
  operativa reservada.
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
  "status": "waiting_payment|payment_reported|payment_rejected|payment_confirmed|delivered|disputed|completed|cancelled",
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
  "cancel_reason": "payment_not_reported_in_time|remitter_cancelled_before_payment|business_unavailable|admin_cancelled|null",
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

Para ordenes Zelle, este endpoint y el reporte de pago requieren que un mensaje
visible del `business_owner` en el chat privado contenga exactamente el Zelle
configurado congelado en la orden. Un saludo u otro mensaje del negocio no
habilita el pago. Si el Zelle no fue compartido, responde
`ORDER_PAYMENT_DETAILS_NOT_SHARED` sin marcar instrucciones como vistas.

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
  "expected_rate_bs_per_usd": "39.500000"
}
```

`receiver_data` es una entrada legacy temporal de 50A, no el contrato final de
50B. Clientes nuevos deben omitirla:

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

Antes de activar 50B1:

- el runtime debe dejar de aceptar/persistir este payload legacy mediante un
  plan de deprecacion compatible;
- un `receiver_data` legacy no reemplaza la coordinacion en chat;
- el endpoint `PUT /api/v1/orders/{id}/receiver-details` es la ruta
  estructurada requerida antes de que el negocio marque Pago Movil enviado.

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
- Si se envia `expected_rate_bs_per_usd`, debe coincidir con la tasa vigente
  del anuncio. Si cambio, responder `ORDER_QUOTE_CHANGED` sin crear la orden.
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
- `receiver_data` no es requisito para crear la orden ni abrir el chat.
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
- El frontend debe abrir el chat despues de recibir la orden creada. Cerrar o
  volver desde la confirmacion previa no llama este endpoint y no crea orden,
  reserva ni consumo de credito.

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
- BUSINESS_DAILY_LIMIT_EXCEEDED
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
- `completion_reason` debe ser `manual_confirmed`,
  `auto_completed_after_24h` o `admin_resolved`; para `admin_resolved`, la
  disputa asociada debe estar cerrada/resuelta;
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

## PUT /api/v1/orders/{id}/receiver-details

Crea los datos estructurados del receptor de Pago Movil requeridos por el flujo
chat-first antes de que el negocio marque enviado. Aunque la UI los represente
como una burbuja compacta, no son `messages.body`.

Request:

```json
{
  "bank": "allowlisted bank code or normalized label",
  "phone": "0414 1234567",
  "document": "V12345678",
  "holder": "Receiver name"
}
```

Rules:

- Solo remitente owner activo.
- La primera creacion requiere `payment_confirmed`.
- `Idempotency-Key` obligatorio.
- Validacion y normalizacion backend:
  - `bank`: codigo del catalogo backend de bancos Pago Movil;
  - `phone`: formato usual del participante, incluyendo `04xx` local o `+58`,
    con espacios, parentesis o guiones opcionales; requiere al menos siete
    digitos y rechaza markup/caracteres de control;
  - `document`: `V|E|J|G|P` mayuscula seguida por 6..10 digitos;
  - `holder`: espacios normalizados, 2..120 caracteres, sin markup de control.
- Campos extra o metadata libre son rechazados.
- El backend liga el recurso a la orden; el request no puede elegir
  `order_id`, actor, visibilidad o receptor.
- No crea mensaje, adjunto, audit con valores, telemetry ni notificacion con
  datos de receptor.
- El recurso protegido y su audit seguro se persisten atomicamente; si el audit
  falla, la escritura falla cerrada.
- El response normal devuelve estado y resumen enmascarado.
- El primer payload valido queda inmutable. Un payload diferente, incluso con
  otra key, responde `ORDER_RECEIVER_DETAILS_ALREADY_SHARED`.
- El mismo payload canonico con otra key devuelve el recurso existente sin
  duplicar audit ni notificacion.
- Lookup de idempotencia/recurso existente ocurre antes del guard de primera
  creacion. Un replay valido puede responder despues de que la orden avance;
  solo una creacion inicial evalua el estado `payment_confirmed`.
- Una correccion requiere contrato futuro; no se hace por chat ni reemplazo
  silencioso.
- Contrato completo y seguridad:
  `slice_50B_p2p_completion_contract_reconciliation/API_CONTRACT.md`.

Errores:

- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- ORDER_RECEIVER_DETAILS_INVALID
- ORDER_RECEIVER_DETAILS_ALREADY_SHARED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- RATE_LIMITED

## GET /api/v1/orders/{id}/receiver-details

Reveal explicito solo para remitente y negocio participantes.

Rules:

- Permitido en `payment_confirmed`, `delivered` o `disputed`.
- `Cache-Control: private, no-store`.
- Cada reveal completo genera audit sin copiar valores.
- Si no puede persistirse el audit del reveal, no se devuelven valores completos.
- Admin/support no usan este endpoint. Un reveal interno futuro requiere ruta,
  permiso, motivo y audit propios.
- No se incluye en detail/list, mensajes, busqueda ni metadata libre.
- Si no fue compartido, responde `404 ORDER_RECEIVER_DETAILS_NOT_FOUND`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- ORDER_RECEIVER_DETAILS_NOT_FOUND
- RATE_LIMITED
- INTERNAL_ERROR si falla el audit obligatorio del reveal

## POST /api/v1/orders/{id}/confirm-received

Confirmacion oficial del remitente owner de que el receptor recibio Pago Movil.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request body: vacio.

Rules:

- Solo remitente owner activo.
- Requiere `orders.status = delivered`.
- Requiere ausencia de disputa `open|in_review`.
- Ejecuta `delivered -> completed` bajo bloqueo transaccional.
- Setea `completion_reason = manual_confirmed` y `completed_at`.
- Consume capacidad operativa reservada exactamente una vez.
- No consume credito publicitario; ya se consumio en `payment_confirmed`.
- Crea un state event y audit `order_completed` sin datos privados.
- Notifica al negocio con copy generico.
- Habilita rating solo cuando el contrato de rating lo permite.
- Replay con misma key no duplica capacidad, evento, audit ni notificacion.
- Una carrera contra apertura de disputa tiene un solo ganador.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_RECEIPT_CONFIRMATION_NOT_ALLOWED
- ORDER_COMPLETION_BLOCKED_BY_DISPUTE
- ORDER_STATE_CONFLICT
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- RATE_LIMITED

## Auto-complete de respaldo

- Puede ejecutar `delivered -> completed` solo cuando
  `auto_complete_at <= now()` y no existe disputa `open|in_review`.
- Usa el mismo caso de uso atomico de `confirm-received`, con
  `completion_reason = auto_completed_after_24h`.
- Consume capacidad una vez y no consume credito otra vez.
- Habilita rating si el contrato de rating lo permite y no hay disputa.
- Recordatorios de 12h/23h y aviso final son seguros e idempotentes.
- Scheduler, singleton, batch, metricas y activacion operativa pertenecen a un
  slice posterior; 50B0 solo define el contrato.

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
status=waiting_payment|payment_reported|payment_rejected|payment_confirmed|delivered|disputed|completed|cancelled|null
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
  "reason": "business_unavailable",
  "payment_not_sent_confirmed": true
}
```

`reason` admite `business_not_responding`, `business_unavailable`,
`customer_mistake` o `choose_another_business`. Omitir el payload conserva
compatibilidad y usa `choose_another_business`.
`payment_not_sent_confirmed` debe ser booleano real; texto como `"true"` no
cuenta como confirmacion.

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
- La transicion se ejecuta bajo bloqueo de la orden. Si pago, expiracion u otra
  cancelacion gano primero, responde `ORDER_STATE_CONFLICT`.
- Si `payment_data_revealed_at` existe, requiere confirmacion explicita
  `payment_not_sent_confirmed = true`.
- La lectura de instrucciones y la cancelacion se serializan bajo el mismo
  bloqueo; el check de confirmacion no puede quedar obsoleto.
- La confirmacion no prueba que no hubo una transferencia; solo registra la
  declaracion del cliente y la ausencia de reporte de pago en NODO.
- Setea `order.status = cancelled`.
- Setea `cancel_reason = remitter_cancelled_before_payment`.
- Si el anuncio no vencio: `ad.status = active` y el credito permanece bloqueado para la publicacion.
- Si el anuncio vencio: materializar `ad.status = archived` y consumir el hold con ledger `expire`.
- Crear state event.
- Liberar la reserva de capacidad una sola vez.
- Auditar `order_cancelled` y `business_capacity_released`.
- No reporta pago ni toca evidencia.
- Orden, reserva, anuncio, evento y audit cambian en una transaccion. Si el
  anuncio ya vencio, su hold se consume y queda archivado dentro de esa misma
  transaccion.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- ORDER_STATE_CONFLICT
- ORDER_PAYMENT_ALREADY_REPORTED
- ORDER_PAYMENT_NOT_SENT_CONFIRMATION_REQUIRED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- RATE_LIMITED

## Integridad concurrente de creacion

- La comprobacion de `active_order_limit` se repite dentro de la transaccion
  final, bajo el mismo bloqueo de negocio usado para reservar capacidad.
- La orden que hace superar el limite debe abortar junto con su reserva.
- Las validaciones previas del marketplace son orientativas; la creacion
  backend es la autoridad final.

## Lifecycle de capacidad

- `waiting_payment`, `payment_reported`, `payment_rejected`,
  `payment_confirmed`, `delivered` y `disputed` conservan la reserva.
- Cancelacion o expiracion libera la reserva una sola vez.
- `completed` consume la reserva una sola vez y reduce la capacidad declarada;
  el monto consumido no reaparece automaticamente como disponible.
- Resolver una disputa aplica la accion terminal resultante: `completed`
  consume y `cancelled` libera.
- El replay de una transicion no duplica reserva, liberacion ni consumo.
