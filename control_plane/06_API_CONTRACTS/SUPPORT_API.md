# SUPPORT_API.md

API para soporte general cliente, soporte por recursos del negocio y cola Admin Web.

## Reglas globales

- Todas las rutas usan `/api/v1`.
- Requieren JWT salvo contrato futuro explicito.
- Mutaciones requieren `Idempotency-Key`.
- Crear/responder/escalar/resolver/cerrar ticket no cambia estados de orden, anuncios, creditos ni disputas.
- Support no puede resolver disputa formal desde este API.
- Responses nunca incluyen `storage_path`, signed URLs persistidas, `account_value`, tokens ni secretos.
- Slice 20C: si el actor opera como staff delegado, el backend debe validar `staff_profiles.status = active`, permiso activo y scope compatible.
- `users.role = support` no basta para saltar restricciones de `staff_permissions` cuando el flujo usa delegacion interna.

## Endpoints cliente/negocio

### POST /api/v1/support/tickets

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-NODO-Surface: client_mini_app|business_mini_app
```

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
  "attachment_ids": ["uuid"]
}
```

Rules:
- `client_general`: remitente/cliente autenticado, sin recurso requerido.
- `client_order`: requiere orden propia del remitente.
- `business_general`: requiere negocio propio aprobado/asociado y access link activo.
- `business_order`: requiere orden del negocio.
- `business_ad`: requiere anuncio propio.
- `business_credit`: requiere recurso de creditos propio.
- `message` max 2000 caracteres.
- Audit `support_ticket_created`.

### GET /api/v1/support/tickets

Query:

```txt
status=optional
scope=optional
cursor=optional
limit=1..50
```

Rules:
- Lista solo tickets propios/participados.
- Cursor pagination.
- No expone mensajes internos.

### GET /api/v1/support/tickets/{id}

Rules:
- Solo requester/participantes autorizados o admin/support.
- Devuelve mensajes con `visibility = participants`.
- No devuelve `support_internal` ni `admin_internal` a usuarios finales.

### POST /api/v1/support/tickets/{id}/messages

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
```

Payload:

```json
{
  "body": "string",
  "attachment_ids": ["uuid"]
}
```

Rules:
- Ticket no cerrado.
- Actor debe ser participante autorizado.
- Audit `support_message_created`.

### POST /api/v1/support/tickets/{id}/attachments

Multipart upload.

Rules:
- MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Maximo 5 MB.
- `file_assets.file_type = support_attachment`.
- `file_assets.resource_type = support_ticket` o `support_message`.
- Response devuelve metadata segura, nunca `storage_path`.
- Audit `support_attachment_uploaded`.

## Endpoints Admin Web

### GET /api/v1/admin/support/tickets

Query:

```txt
status=optional
scope=optional
category=optional
priority=optional
assigned_support_user_id=optional
cursor=optional
limit=1..50
```

Rules:
- `support`, `admin`, `super_admin`.
- Cursor pagination.
- List view usa masking y resumen.
- Para staff delegado, requiere `view_support_queue` o `view_assigned_support_tickets` segun scope.

### GET /api/v1/admin/support/tickets/{id}

Detalle Admin Web.

Rules:
- Incluye mensajes, eventos y adjuntos como metadata segura.
- No incluye `storage_path`.
- No incluye body completo en audit.
- Para staff con `assigned_only`, el ticket debe estar asignado al staff.

### POST /api/v1/admin/support/tickets/{id}/messages

Headers:

```txt
Idempotency-Key: requerido
```

Payload:

```json
{
  "body": "string",
  "visibility": "participants|support_internal|admin_internal",
  "attachment_ids": ["uuid"]
}
```

Rules:
- `support`, `admin`, `super_admin`.
- `support` puede usar `participants` y `support_internal`.
- `admin_internal` solo `admin`/`super_admin`.
- Audit `support_message_created`.
- Para staff delegado, requiere `reply_support_ticket` y scope compatible.

### POST /api/v1/admin/support/tickets/{id}/assign

Headers:

```txt
Idempotency-Key: requerido
```

Payload:

```json
{
  "assigned_support_user_id": "uuid",
  "reason": "string"
}
```

Rules:
- Assignee debe tener rol `support`, `admin` o `super_admin` y status `active`.
- Si assignee es staff delegado, debe tener `staff_profiles.status = active`.
- Reason obligatorio.
- Audit `support_ticket_assigned`.
- Para actor staff delegado, requiere `assign_support_ticket`.

### POST /api/v1/admin/support/tickets/{id}/escalate

Payload:

```json
{
  "reason": "string",
  "existing_dispute_id": "uuid|null"
}
```

Rules:
- Reason obligatorio.
- Setea `status = escalated`.
- Si `existing_dispute_id` se envia, solo vincula metadata/contexto a una disputa existente visible para el actor.
- No crea disputa nueva.
- No resuelve disputa.
- Audit `support_ticket_escalated`; si hay disputa existente vinculada, audit `support_ticket_linked_to_dispute`.
- Para actor staff delegado, requiere `escalate_support_ticket`.

### POST /api/v1/admin/support/tickets/{id}/resolve

Payload:

```json
{
  "reason": "string"
}
```

Rules:
- Reason obligatorio.
- Setea `status = resolved`.
- Resolver ticket no resuelve disputa formal.
- Audit `support_ticket_resolved`.
- Para actor staff delegado, requiere `resolve_support_ticket`.

### POST /api/v1/admin/support/tickets/{id}/close

Payload:

```json
{
  "reason": "string"
}
```

Rules:
- Reason obligatorio.
- Solo `resolved -> closed`.
- Audit `support_ticket_closed`.
- Para actor staff delegado, requiere `close_support_ticket`.

### POST /api/v1/admin/support/tickets/{id}/attachments/{file_id}/view-url

Payload:

```json
{
  "reason": "string"
}
```

Rules:
- Solo `support`, `admin`, `super_admin` autorizado.
- Reason obligatorio.
- Signed URL expira maximo en 5 minutos.
- Nunca persistir signed URL.
- Audit `support_attachment_viewed`.
- Para actor staff delegado, requiere `view_support_attachment`.

## Errores esperados

- SUPPORT_TICKET_NOT_FOUND
- SUPPORT_TICKET_STATUS_INVALID
- SUPPORT_SCOPE_INVALID
- SUPPORT_CATEGORY_INVALID
- SUPPORT_ATTACHMENT_INVALID
- SUPPORT_ATTACHMENT_TOO_LARGE
- SUPPORT_ATTACHMENT_TYPE_NOT_ALLOWED
- SUPPORT_ATTACHMENT_NOT_FOUND
- SUPPORT_ATTACHMENT_ACCESS_DENIED
- SUPPORT_ASSIGNMENT_NOT_ALLOWED
- SUPPORT_ASSIGNEE_INVALID
- SUPPORT_ESCALATION_NOT_ALLOWED
- SUPPORT_MESSAGE_REQUIRED
- STAFF_PERMISSION_DENIED
- STAFF_ASSIGNMENT_INVALID
- ADMIN_REASON_REQUIRED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- FORBIDDEN
- UNAUTHENTICATED
- RATE_LIMITED
- STORAGE_UNAVAILABLE
