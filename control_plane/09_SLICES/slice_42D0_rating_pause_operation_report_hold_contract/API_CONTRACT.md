# API Contract

Este documento define interfaces por fases. 42E1 implementa el reporte
estructurado y 42F1 implementa hold y liberacion Admin. Telegram permanece
futuro hasta 42F2.

## Rating y pausa temporal

La creacion idempotente de un rating valido debe persistir, en la misma unidad
transaccional futura:

```txt
ad_publication_paused_until =
  max(current_ad_publication_paused_until, database_now + 15 minutes)
```

El replay del mismo rating devuelve el resultado existente y no vuelve a
extender la pausa. Dos ratings distintos concurrentes conservan el mayor valor.

## POST /api/v1/orders/{order_id}/operation-report

Actor: cliente/remitente propietario de la orden.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-NODO-Surface: client_mini_app
```

Payload:

```json
{
  "category": "order_help|payment_report_help|suspicious_activity|other",
  "message": "string"
}
```

Reglas:

- `order_id` proviene del path y debe identificar una orden propia.
- El payload no acepta `business_id`, rating, estrellas ni campos extra.
- El backend deriva `business_id = order.business_id`.
- El backend crea un ticket con `scope = client_order` y marca interna
  `report_kind = structured_operation_report`.
- La razon privada puede ser visible a Admin/Support autorizados, pero no al
  negocio, Telegram ni audit.
- Falta de orden y orden ajena responden `ORDER_NOT_FOUND` para evitar IDOR.
- Solo aplican los estados reportables definidos en `README.md`.
- Maximo un reporte estructurado activo por orden. El replay con la misma llave
  devuelve el recurso existente; otra llave responde
  `OPERATION_REPORT_DUPLICATE`.
- Se aplican rate limits por cliente y por orden.
- 42F1 extiende 42E1 y consulta la pausa dentro de la transaccion durable.
- Si
  `database_now < ad_publication_paused_until`, ticket y hold deben crearse de
  forma atomica. Si la pausa ya vencio, se crea el ticket sin hold.
- Un ticket generico creado por `POST /support/tickets` nunca crea hold.
- La respuesta usa `Cache-Control: private, no-store`.

Response 201:

```json
{
  "data": {
    "ticket": {}
  },
  "request_id": "req_..."
}
```

La respuesta del cliente no incluye datos internos del negocio, causa de pausa,
rating, estrellas, existencia de hold ni destinatarios Telegram.

## Concepto durable de hold

La migracion 0052 de 42F1 modela:

```txt
business_publication_holds
  id
  business_id
  order_id
  support_ticket_id
  status = active|released
  reason_type = structured_operation_report
  created_at
  released_at
  released_by
  release_reason
```

Debe impedir holds activos duplicados para la misma orden/ticket y conservar el
historial. Si existen varios holds reales para un negocio, todos deben estar
liberados antes de permitir publicacion.

## POST /api/v1/admin/business-publication-holds/{hold_id}/release

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
```

Payload:

```json
{
  "reason": "string"
}
```

Reglas:

- `admin` y `super_admin` activos pueden ejecutar.
- 42F1 autoriza solo `admin` y `super_admin`. La delegacion futura a Support
  requiere ampliar primero el constraint durable de permisos y demostrar scope
  contra el ticket asociado.
- El rol base `support` sin ese permiso recibe `FORBIDDEN`.
- Reason e idempotencia son obligatorios.
- El replay no duplica audit ni cambia el timestamp original.
- Cerrar, resolver o archivar el ticket no llama implicitamente esta ruta.
- La respuesta usa `Cache-Control: private, no-store`.

## Alerta Telegram Admin

Cada reporte estructurado encola una alerta para cada usuario `admin` o
`super_admin` activo con Telegram vinculado. No se crean jobs role-only.

Texto permitido:

```txt
Alerta NODO
Nuevo reporte de operacion
Orden: NODO-XXXXXX
Estado: requiere revision
Publicacion pausada para revision: si/no
Revisar Admin Web
```

La deduplicacion minima es `operation_report:{report_id}:{recipient_user_id}`.
Si no existe destinatario elegible, ticket y hold conservan exito; se registra
`ADMIN_TELEGRAM_ALERT_NOT_CONFIGURED` como error interno observable. Un fallo de
Telegram tampoco revierte ticket/hold y el retry no duplica alertas.

## Errores publicos

- `BUSINESS_PUBLICATION_TEMPORARILY_UNAVAILABLE`: 409, pausa activa.
- `BUSINESS_PUBLICATION_UNDER_REVIEW`: 409, hold activo.
- `OPERATION_REPORT_NOT_ALLOWED`: 409, estado no reportable.
- `OPERATION_REPORT_DUPLICATE`: 409, ya existe reporte activo para la orden.
- `ORDER_NOT_FOUND`: 404, orden inexistente o no visible para el actor.
- `BUSINESS_PUBLICATION_HOLD_NOT_FOUND`: 404.
- `BUSINESS_PUBLICATION_HOLD_ALREADY_RELEASED`: 409.
- `FORBIDDEN`: 403, actor sin permiso de liberacion.

`ADMIN_TELEGRAM_ALERT_NOT_CONFIGURED` es interno y nunca convierte la creacion
del ticket/hold en error publico.
