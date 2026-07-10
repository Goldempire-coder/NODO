# SUPPORT_API.md

## Objetivo

API para soporte general cliente, soporte por orden, soporte negocio y cola admin/support.

## Endpoints usuario/negocio

### POST /api/v1/support/tickets

Headers:
- `Authorization`
- `Idempotency-Key`

Payload:
```json
{
  "scope": "client_general|order_support|business_general",
  "order_id": "uuid|null",
  "business_id": "uuid|null",
  "subject": "string",
  "message": "string"
}
```

Rules:
- `order_support` requiere ownership o participacion en la orden.
- `business_general` requiere negocio propio aprobado/asociado.
- Crear ticket no cambia estados de orden.

Audit: `support_ticket_created`.

### GET /api/v1/support/tickets

Rules:
- Lista solo tickets propios/participados.
- Cursor pagination.
- No expone datos sensibles completos.

### GET /api/v1/support/tickets/{id}

Rules:
- Solo participantes autorizados o admin/support.

### POST /api/v1/support/tickets/{id}/messages

Headers:
- `Authorization`
- `Idempotency-Key`

Payload:
```json
{ "body": "string" }
```

Rules:
- Ticket abierto/no cerrado.
- No cambia estados de orden.

Audit: `support_message_created`.

### POST /api/v1/support/tickets/{id}/attachments

Rules:
- Storage privado.
- `file_assets.resource_type = support_ticket` o `support_message`.
- `storage_path` nunca se expone.

## Admin/support endpoints

### GET /api/v1/admin/support/tickets

Rules:
- `support`, `admin`, `super_admin` pueden ver cola segun RBAC.
- Filtros: `status`, `scope`, `cursor`, `limit`.

### POST /api/v1/admin/support/tickets/{id}/escalate

Payload:
```json
{ "reason": "string", "target": "dispute|admin_internal" }
```

Rules:
- Escalar a disputa requiere contrato de disputa y orden elegible.
- Support puede escalar si RBAC lo permite; resolver disputa no queda incluido aqui.

Audit: `support_ticket_escalated`, `support_ticket_linked_to_dispute` si aplica.

### POST /api/v1/admin/support/tickets/{id}/resolve

Payload:
```json
{ "reason": "string" }
```

Rules:
- Resolver ticket de soporte no resuelve disputa ni cambia estados de orden.
- Reason obligatorio.

Audit: `support_ticket_resolved`.

### POST /api/v1/admin/support/tickets/{id}/close

Payload:
```json
{ "reason": "string" }
```

Audit: `support_ticket_closed`.

