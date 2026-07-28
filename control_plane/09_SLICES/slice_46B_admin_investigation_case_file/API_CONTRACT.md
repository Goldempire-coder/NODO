# Slice 46B API Contract

Estado: STAGING_DEPLOYED_PENDING_OWNER_SMOKE

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
- `section`: `all|orders|support_tickets|business_intakes|evidence|timeline`.
  Default `all`.
- `cursor`: cursor opaco para la seccion solicitada. No aplica con
  `section=all`.

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
      "case_title": "Ficha de investigacion",
      "anchor_reason": "order_anchor",
      "last_activity_at": "2026-07-27T00:00:00Z",
      "counts": {
        "orders": 1,
        "support_tickets": 2,
        "business_intakes": 0,
        "timeline_events": 5
      }
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
      "status": "ok",
      "items": [],
      "truncated": false,
      "next_cursor": null,
      "error": null
    },
    "support_tickets": {
      "status": "ok",
      "items": [],
      "truncated": false,
      "next_cursor": null,
      "error": null
    },
    "business_intakes": {
      "status": "ok",
      "items": [],
      "truncated": false,
      "next_cursor": null,
      "error": null
    },
    "evidence": {
      "status": "ok",
      "payment_report_present": false,
      "chat_evidence_available": false,
      "documents": [],
      "attachments": [],
      "truncated": false,
      "next_cursor": null,
      "total_count": 0,
      "error": null
    },
    "timeline": {
      "status": "ok",
      "items": [],
      "truncated": false,
      "next_cursor": null,
      "error": null
    },
    "review_checklist": [
      {
        "code": "RELATED_ORDER_PRESENT",
        "label": "Orden relacionada encontrada",
        "status": "present",
        "action_route": "admin://order/uuid"
      }
    ],
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
- No debe devolver `severity_hint`, `suggested_next_step` ni conclusiones
  narrativas sobre culpa, fraude, pago valido o recuperacion.
- `review_checklist` solo puede reflejar checks deterministas basados en datos:
  `present`, `missing`, `not_checked` o `not_authorized`.

## Paginacion

- `section=all` devuelve la primera pagina de cada seccion.
- Para cargar mas datos de una seccion se usa `section=<nombre>` y el
  `cursor` devuelto por esa misma seccion.
- El cursor debe ser opaco, estar ligado a la seccion y al anchor, y no debe
  revelar IDs internos no necesarios.
- Los filtros de permisos, `include_archived`, ordenamiento y cursor se aplican
  antes de `LIMIT`.
- Una seccion con fallo parcial debe devolver `status=partial_error` o
  `status=error` con mensaje seguro. Las demas secciones deben seguir
  disponibles cuando sea posible.

## Timeline

- El timeline usa allowlist de eventos:
  - orden creada;
  - reporte de pago recibido;
  - estado de orden cambiado;
  - ticket creado;
  - ticket resuelto/cerrado;
  - intake recibido/aprobado/rechazado;
  - alerta administrativa relacionada.
- No incluye `metadata_json` crudo.
- No incluye `reason` privada, cuerpos de mensajes, adjuntos, payloads de
  proveedor ni texto libre del usuario.
- La ficha puede decir "evento relacionado", pero no "mismo caso" salvo que la
  relacion sea por ID directo.

## Reglas Por Rol

- `super_admin` y `admin`: ficha allowlist completa.
- `support` activo: solo lectura y limitado a tickets visibles por la politica
  de soporte vigente y resumen operativo estrictamente necesario.
- Si `support` no puede ver el anchor, responder `404` en vez de filtrar datos.
- `support` no recibe documentos privados de intake, `metadata_json` de audit,
  campos de riesgo interno ni evidencia descargable.

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
- `section`
- `include_archived`
- si hay secciones truncadas
- secciones con error seguro
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
- `ADMIN_CASE_FILE_CURSOR_INVALID`: cursor invalido, alterado o de otra
  seccion/anchor/filtro.
- `ADMIN_CASE_FILE_SECTION_UNAVAILABLE`: error parcial seguro dentro de una
  seccion; no invalida las demas.
- `FORBIDDEN`: actor sin permiso.
- `RATE_LIMITED`: exceso de investigacion.

## Cache

- `Cache-Control: private, no-store`
