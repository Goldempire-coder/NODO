# API_CONTRACT.md

Todas las rutas usan `/api/v1`, JWT, backend RBAC, rate limit y errores seguros.

## Endpoints cliente/negocio

### POST /api/v1/support/tickets

Headers:
- `Authorization`
- `Idempotency-Key`
- `X-NODO-Surface`

Payload:

```json
{
  "scope": "client_general|client_order|business_general|business_order|business_ad|business_credit",
  "category": "technical_issue|account_access|order_help|payment_report_help|business_access|credits_help|suspicious_activity|other",
  "subject": "string",
  "message": "string",
  "order_id": "uuid|null",
  "business_id": "uuid|null",
  "ad_id": "uuid|null",
  "credit_purchase_id": "uuid|null",
  "attachment_ids": ["file_asset_id"]
}
```

Rules:
- `client_general` no requiere recurso asociado.
- `client_order` requiere orden propia del remitente.
- `business_general` requiere negocio aprobado/asociado activo.
- `business_order` requiere orden del negocio.
- `business_ad` requiere anuncio propio.
- `business_credit` requiere compra/wallet/ledger propio segun recurso.
- Crear ticket no cambia estados de orden, anuncio, credito ni disputa.

### GET /api/v1/support/tickets

Query:
- `status`
- `scope`
- `cursor`
- `limit`

Rules:
- Devuelve solo tickets propios/participados.
- Cursor pagination.
- No expone `storage_path` ni bodies internos.

### GET /api/v1/support/tickets/{id}

Detalle propio con mensajes visibles para participantes.

### POST /api/v1/support/tickets/{id}/messages

Headers:
- `Authorization`
- `Idempotency-Key`

Payload:

```json
{
  "body": "string",
  "attachment_ids": ["file_asset_id"]
}
```

Rules:
- Ticket no debe estar `closed`.
- Usuario debe ser participante autorizado.
- No cambia estados de orden/anuncio/credito.

### POST /api/v1/support/tickets/{id}/attachments

Multipart upload.

Rules:
- MIME: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Max 5 MB.
- `file_assets.file_type = support_attachment`.
- `resource_type = support_ticket` o `support_message` segun contexto.
- Response nunca incluye `storage_path`.

## Endpoints Admin Web

### GET /api/v1/admin/support/tickets

Query:
- `status`
- `scope`
- `category`
- `priority`
- `assigned_support_user_id`
- `cursor`
- `limit`

Rules:
- `support`, `admin`, `super_admin` pueden ver cola.
- Cursor pagination.
- Masking por defecto.

### GET /api/v1/admin/support/tickets/{id}

Detalle admin/support con mensajes, eventos y metadata segura.

### POST /api/v1/admin/support/tickets/{id}/messages

Permite responder desde Admin Web.

Headers:
- `Idempotency-Key`

Payload:

```json
{
  "body": "string",
  "visibility": "participants|support_internal|admin_internal",
  "attachment_ids": ["file_asset_id"]
}
```

### POST /api/v1/admin/support/tickets/{id}/assign

Headers:
- `Idempotency-Key`

Payload:

```json
{
  "assigned_support_user_id": "uuid",
  "reason": "string"
}
```

Rules:
- Assignee debe ser `support|admin|super_admin` activo.
- Reason obligatorio.
- Audit `support_ticket_assigned`.

### POST /api/v1/admin/support/tickets/{id}/escalate

Payload:

```json
{
  "reason": "string",
  "existing_dispute_id": "uuid|null"
}
```

Rules:
- Marca ticket `escalated`.
- Puede guardar link a disputa existente solo si existe y actor puede verla.
- No crea disputa en 20B.

### POST /api/v1/admin/support/tickets/{id}/resolve

Payload:

```json
{ "reason": "string" }
```

Rules:
- Resolver ticket no resuelve disputa formal.
- Reason obligatorio.

### POST /api/v1/admin/support/tickets/{id}/close

Payload:

```json
{ "reason": "string" }
```

Rules:
- Solo `resolved -> closed`.
- Reason obligatorio.

### POST /api/v1/admin/support/tickets/{id}/attachments/{file_id}/view-url

Payload:

```json
{ "reason": "string" }
```

Rules:
- Signed URL corta max 5 minutos.
- Reason obligatorio.
- Audit `support_attachment_viewed`.
- Nunca persistir signed URL.
