# MESSAGES_API.md

Contrato API canonico para mensajes y adjuntos privados de orden.

## Endpoints

- GET /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/share-payment-details
- POST /api/v1/orders/{id}/share-zelle
- POST /api/v1/orders/{id}/message-attachments

## Reglas comunes

- Requiere Authorization Bearer JWT.
- Requiere ownership backend.
- Remitter solo opera orden propia.
- Business owner solo opera orden de su negocio aprobado.
- Admin/super_admin pueden leer para revision segun contrato de evidencia
  explicito, excepto cuerpos de `waiting_payment` mediante este endpoint
  general.
- Support solo lectura cuando RBAC lo permite, excepto cuerpos de
  `waiting_payment` mediante este endpoint general.
- Guest no accede.
- No filtrar existencia de ordenes ajenas.
- Rate limit obligatorio por usuario, orden, IP y ruta.
- No exponer `storage_path`, signed URLs, tokens ni secretos.
- El Zelle o wallet USDT completo solo puede aparecer dentro de un mensaje
  privado de la orden despues de que el negocio lo comparta manualmente o con
  la accion autorizada. No se copia a logs, audit, Telegram o admin
  notifications.
- Mensajes deben sanitizarse antes de mostrarse.
- Pago Movil se comparte mediante el recurso estructurado `receiver-details`
  contratado en `ORDERS_API.md`. La UI puede representarlo como una burbuja
  dentro del chat, pero sus valores no se persisten en `messages.body`.
- Un mensaje libre con telefono, documento, banco o titular no crea ni reemplaza
  `receiver-details`, no autoriza reveal y no satisface el requisito para que el
  negocio marque Pago Movil enviado.
- El reveal completo pertenece solo a cliente y negocio participantes mediante
  el endpoint autorizado. Admin y Support requieren un contrato separado con
  RBAC y auditoria; este endpoint general de mensajes no concede ese acceso.

## GET /api/v1/orders/{id}/messages

Query:

- `cursor` opcional.
- `limit` opcional, 1..50, default 25.
- Sin cursor, devuelve la ventana mas reciente.
- Con `cursor`, devuelve la ventana inmediatamente anterior.
- `items` siempre se ordena de antiguo a nuevo dentro de cada ventana.

Response:

```json
{
  "order_id": "uuid",
  "order": {
    "id": "uuid",
    "public_order_code": "NODO-A1234567",
    "status": "payment_reported",
    "amount_usd": "50.00",
    "amount_bs_calculated": "1975.00"
  },
  "items": [
    {
      "id": "uuid",
      "sender_role": "remitter",
      "body": "safe sanitized text",
      "visibility": "parties",
      "status": "visible",
      "attachments": [
        {
          "id": "uuid",
          "file_asset_id": "uuid",
          "file_type": "message_attachment",
          "mime_type": "image/png",
          "size_bytes": 12345,
          "created_at": "timestamp"
        }
      ],
      "created_at": "timestamp"
    }
  ],
  "system_messages": [
    {
      "id": "system:negotiation-created:uuid",
      "sender_role": "system",
      "body": "Negociacion creada. Coordinen por aqui. No envies el pago hasta que el negocio comparta sus datos.",
      "attachments": []
    }
  ],
  "capabilities": {
    "can_send_message": true,
    "can_open_dispute": false,
    "can_share_payment_details": false,
    "payment_details_shared": false,
    "can_report_payment": false
  },
  "next_cursor": "opaque-or-null"
}
```

`system_messages` es derivado y no se persiste, audita ni envia por Telegram.
Solo se devuelve en la primera pagina.
Si la orden queda `cancelled` o `completed`, los participantes directos pueden
seguir leyendo el chat como historial cerrado. El backend devuelve un mensaje de
sistema terminal, pero `can_send_message = false`; no se permiten mensajes,
adjuntos ni acciones nuevas desde el composer.
`order` es un resumen allowlist de la orden actual para que el chat sincronice
estado y acciones sin navegar fuera del chat. Cliente recibe el payload publico;
Negocio recibe el payload operacional enmascarado. No incluye `storage_path`,
URLs firmadas, `account_value`, cuerpos privados adicionales ni datos sensibles
no autorizados.
`next_cursor` apunta a mensajes anteriores; nunca obliga a la UI activa a
empezar por la pagina mas antigua.

Errors:

- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- FORBIDDEN
- RATE_LIMITED
- UNAUTHENTICATED

## POST /api/v1/orders/{id}/messages

Headers:

- Idempotency-Key required.

Request:

```json
{
  "body": "message text",
  "attachment_ids": ["uuid"]
}
```

Validation:

- `body` required when `attachment_ids` is empty.
- `body` max length 2000 characters.
- Max 5 attachments per message.
- Attachment ids must belong to same order and actor.

Allowed order states:

- waiting_payment
- payment_reported
- payment_rejected
- payment_confirmed
- delivered
- disputed

Response:

```json
{
  "message": {
    "id": "uuid",
    "order_id": "uuid",
    "sender_role": "business_owner",
    "body": "safe sanitized text",
    "visibility": "parties",
    "status": "visible",
    "attachments": [],
    "created_at": "timestamp"
  }
}
```

Idempotency:

- Same key + same payload returns same message.
- Same key + different payload returns IDEMPOTENCY_PAYLOAD_MISMATCH.

En `waiting_payment`, solo cliente y owner del negocio participantes pueden
leer/escribir. Admin/support no pueden usar este endpoint general para obtener
cuerpos completos en ese estado. Los terceros reciben `ORDER_NOT_FOUND`.
En `cancelled` por cancelacion previa al reporte de pago, solo los dos
participantes pueden leer el historial por este endpoint general. Admin,
Support, Super Admin y terceros reciben `ORDER_NOT_FOUND`; la revision interna
debe usar superficies dedicadas y auditadas.

Ningun texto de chat, incluido `recibido`, `confirmado` o `pago enviado`,
ejecuta transiciones, consume creditos, consume capacidad o sustituye los
endpoints oficiales.

Audit:

- message_created
- dispute_message_created when order is in disputed context
- order_chat_off_platform_solicitation_detected when business-owner message matches anti-evasion rules. This event must not include full message body.

Counterparty notification:

- A participant message enqueues exactly one Telegram job for the other party.
- Client/remitter -> business owner uses `order_message_created_business`.
- Business owner -> client/remitter uses `order_message_created_client`.
- Dedupe binds `order_id`, `message_id`, notification type and recipient.
- Telegram metadata contains the order code and destination route, never message
  body, attachment IDs, `file_asset_id`, `storage_path`, signed URLs, payment
  instructions, account data, PINs, tokens or secrets.
- Business chat link:
  `/business/?view=business-chat&order_id={order_id}`.
- Client chat link: `/?view=order-chat&order_id={order_id}`.
- The destination endpoint revalidates order ownership; a deep link is not
  authorization.

Internal admin alert:

- business-owner messages may create `admin_notifications.notification_type = order_chat_off_platform_solicitation`.
- The message remains visible to both parties.
- The alert links to `admin://order/{id}`.
- Notification metadata may include `order_id`, `message_id`, `rule_id`, `severity`, `matched_phrase` as a bounded canonical detection signal without surrounding message text, and `sender_role`.
- Notification metadata must not include `body`, `message_body`, `storage_path`, signed URLs, `account_value`, tokens, PINs or full payment instructions.
- Admin-notification persistence failure must not block a validated message; the backend records a safe operational failure without message content.

Errors:

- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- MESSAGE_NOT_ALLOWED
- MESSAGE_BODY_REQUIRED
- MESSAGE_ATTACHMENT_INVALID
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- FORBIDDEN
- RATE_LIMITED
- UNAUTHENTICATED
- VALIDATION_ERROR

## POST /api/v1/orders/{id}/share-payment-details

Accion compacta exclusiva del owner del negocio para Zelle o USDT. La ruta
`share-zelle` se conserva como alias legacy exclusivo de Zelle.

Rules:

- `Idempotency-Key` requerido.
- Orden propia del negocio, `waiting_payment`, metodo `zelle|usdt_trc20`.
- Inserta una sola vez un mensaje privado con la cuenta configurada congelada
  en la orden y el titular cuando existe.
- Un retry con otra key tampoco duplica el mensaje.
- El cliente queda con `can_report_payment = true`.
- La cuenta configurada no dispara alerta anti-evasion.
- Frases para sacar la operacion de NODO u otros contactos externos siguen
  generando la alerta conservadora.
- Audit `business_payment_details_shared` guarda IDs seguros, nunca la cuenta.

Para `usdt_trc20`, el cliente no puede revelar la wallet ni reportar pago hasta
que el negocio use esta accion. La UI muestra `Compartir wallet` y advierte:
`Confirma con el negocio la red exacta antes de enviar.`

La Mini App Cliente presenta ambos metodos con la misma experiencia compacta:
una burbuja dentro del chat con el dato autorizado, monto y accion `Copiar`.
Copiar ocurre localmente y no agrega el valor a logs, audit, telemetry o
notificaciones. El reporte USDT se envia sin exigir `tx_hash`; si un cliente
legacy lo aporta, se valida como evidencia opcional y no reemplaza la
verificacion manual del negocio.
- Telegram avisa que existe un mensaje nuevo, nunca copia su cuerpo.

Errors:

- ORDER_NOT_FOUND
- ORDER_STATUS_INVALID
- ORDER_STATE_CONFLICT
- ORDER_PAYMENT_METHOD_UNAVAILABLE
- IDEMPOTENCY_KEY_REQUIRED
- RATE_LIMITED

## POST /api/v1/orders/{id}/message-attachments

Headers:

- Idempotency-Key required.

Request:

- multipart/form-data with `file`.

Storage:

- Uses `file_assets`.
- `resource_type = message`.
- `file_type = message_attachment`.
- Private storage required.
- If private storage is unavailable in runtime normal, return STORAGE_UNAVAILABLE.

Allowed MIME:

- image/jpeg
- image/png
- image/webp
- application/pdf

Max size:

- 5 MB.

Response:

```json
{
  "attachment": {
    "id": "uuid",
    "file_asset_id": "uuid",
    "file_type": "message_attachment",
    "mime_type": "image/png",
    "size_bytes": 12345,
    "created_at": "timestamp"
  }
}
```

Audit:

- message_attachment_uploaded

Errors:

- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- MESSAGE_ATTACHMENT_INVALID
- MESSAGE_ATTACHMENT_TOO_LARGE
- MESSAGE_ATTACHMENT_TYPE_NOT_ALLOWED
- STORAGE_UNAVAILABLE
- STORAGE_UPLOAD_FAILED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- FORBIDDEN
- RATE_LIMITED
- UNAUTHENTICATED

## POST /api/v1/orders/{id}/message-attachments/{attachment_id}/view-url

Purpose:

- Allows a direct order participant to explicitly open an image/PDF shared in
  the order chat.
- Intended for Cliente and Negocio chat surfaces only.

Authorization:

- Only the remitter owner of the order or the participating business owner may
  open the attachment.
- Admin, Super Admin, Support and unrelated users receive generic
  `ORDER_NOT_FOUND` through this endpoint. Internal review must use the
  dedicated audited Admin evidence surface.
- The attachment must belong to the same order, must already be attached to a
  visible message, and must be active.

Response:

```json
{
  "url": "temporary-signed-url",
  "expires_in_seconds": 300,
  "download_filename": "nodo-message-attachment-12345678.png"
}
```

Headers:

- `Cache-Control: private, no-store`

Privacy:

- Response never includes `storage_path`, `file_asset_id`, message body,
  account values or permanent URLs.
- Message list responses continue to expose only attachment metadata needed to
  render an explicit open action.

Audit:

- `message_attachment_viewed`
- Metadata allowlist: `order_id`, `message_id`, `mime_type`, `size_bytes`.

Errors:

- ORDER_NOT_FOUND
- ORDER_STATUS_INVALID
- MESSAGE_ATTACHMENT_NOT_FOUND
- STORAGE_UNAVAILABLE
- RATE_LIMITED
- UNAUTHENTICATED
