# Slice 46B API Contract

Estado: DRAFT

Builder debe mapear primero si este contrato ya puede componerse con endpoints
existentes. Si no, la opcion recomendada es crear endpoint dedicado:

```txt
GET /api/v1/admin/investigation/case-file
```

Headers:

- `Authorization: Bearer <admin session>`

Query:

- `anchor_type`: `user|business|business_intake|order|support_ticket`
- `anchor_id`: UUID
- `limit`: entero 1 a 50 por grupo. Default 25.
- `include_archived`: boolean. Default `true`.

## Respuesta Objetivo

```json
{
  "data": {
    "anchor": {
      "type": "order",
      "id": "uuid",
      "title": "Orden NODO-1234",
      "status": "waiting_payment",
      "action_route": "admin://order/uuid"
    },
    "summary": {
      "case_title": "Cliente reporta pago sin recordar negocio",
      "severity_hint": "normal",
      "last_activity_at": "2026-07-27T00:00:00Z",
      "suggested_next_step": "Revisar ordenes recientes y ticket activo"
    },
    "participants": {
      "client": {
        "user_id": "uuid",
        "display_name": "Cliente",
        "telegram_hint": "407*****766",
        "action_route": "admin://user/uuid"
      },
      "business": {
        "business_id": "uuid",
        "name": "Casa Cambio Centro",
        "status": "approved",
        "action_route": "admin://business/uuid"
      },
      "business_owner": {
        "user_id": "uuid",
        "telegram_hint": "584*****910",
        "action_route": "admin://user/uuid"
      }
    },
    "orders": {
      "items": [],
      "truncated": false,
      "next_cursor": null
    },
    "support_tickets": {
      "items": [],
      "truncated": false,
      "next_cursor": null
    },
    "business_intakes": {
      "items": [],
      "truncated": false
    },
    "evidence": {
      "payment_report_present": false,
      "chat_evidence_available": false,
      "documents": [],
      "attachments": []
    },
    "timeline": [],
    "warnings": [],
    "disclaimer": "Ficha de investigacion. No determina responsabilidad ni garantiza recuperacion."
  },
  "request_id": "req_..."
}
```

## Reglas De Datos

- La ficha puede devolver IDs internos necesarios para abrir pantallas admin.
- Telefonos y Telegram deben ir enmascarados.
- Montos de orden pueden verse porque Admin ya los opera.
- Datos bancarios, wallets o instrucciones de pago completas no deben aparecer.
- Adjuntos y documentos se muestran como metadata segura:
  - tipo;
  - MIME;
  - tamano;
  - fecha;
  - disponibilidad;
  - ruta admin para abrir con endpoint auditado, si ya existe.
- La respuesta inicial no debe devolver signed URLs ni `storage_path`.
- No debe devolver cuerpos completos de mensajes salvo que el endpoint sea
  explicitamente de evidencia de chat y ya tenga auditoria separada.

## Relacion Con 46A

Los resultados de 46A pueden agregar una ruta nueva:

```json
{
  "action_route": "admin://case-file/order/uuid"
}
```

La ruta anterior a pantallas directas puede mantenerse. 46B no debe romper la
navegacion existente de 46A.

## Auditoria

Evento obligatorio:

- `admin_investigation_case_file_viewed`

Metadata permitida:

- `anchor_type`
- `anchor_id`
- conteo por grupo
- `include_archived`
- si hay secciones truncadas
- `request_id`

Metadata prohibida:

- cuerpos de mensajes;
- texto libre escrito por usuarios;
- texto crudo de busqueda 46A;
- URLs firmadas;
- storage paths;
- datos bancarios completos;
- secretos o tokens.

## Errores

- `ADMIN_CASE_FILE_ANCHOR_INVALID`: anchor desconocido o formato invalido.
- `ADMIN_CASE_FILE_ANCHOR_NOT_FOUND`: no existe o no es visible para Admin.
- `FORBIDDEN`: actor sin permiso.
- `RATE_LIMITED`: exceso de investigacion.

## Cache

- `Cache-Control: private, no-store`
