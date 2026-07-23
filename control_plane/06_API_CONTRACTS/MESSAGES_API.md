# MESSAGES_API.md

Contrato API canonico para mensajes y adjuntos privados de orden.

## Endpoints

- GET /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/message-attachments

## Reglas comunes

- Requiere Authorization Bearer JWT.
- Requiere ownership backend.
- Remitter solo opera orden propia.
- Business owner solo opera orden de su negocio aprobado.
- Admin/super_admin pueden leer para revision.
- Support solo lectura cuando RBAC lo permite.
- Guest no accede.
- No filtrar existencia de ordenes ajenas.
- Rate limit obligatorio por usuario, orden, IP y ruta.
- No exponer `storage_path`, signed URLs, full payment instructions, `account_value`, tokens ni secretos.
- Mensajes deben sanitizarse antes de mostrarse.

## GET /api/v1/orders/{id}/messages

Query:

- `cursor` opcional.
- `limit` opcional, 1..50, default 25.

Response:

```json
{
  "order_id": "uuid",
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
  "next_cursor": "opaque-or-null"
}
```

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

Audit:

- message_created
- dispute_message_created when order is in disputed context
- order_chat_off_platform_solicitation_detected when business-owner message matches anti-evasion rules. This event must not include full message body.

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
