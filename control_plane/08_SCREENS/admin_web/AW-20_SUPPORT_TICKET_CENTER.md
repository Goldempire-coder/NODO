# AW-20_SUPPORT_TICKET_CENTER.md

## Surface

Admin Web Desktop.

## Objetivo

Operar la cola de tickets de soporte sin mezclarla con chat operativo ni disputa formal.

## Layout

- Sidebar Admin Web.
- Top bar administrativa.
- Tabla densa de tickets.
- Filtros por:
  - status
  - scope
  - category
  - priority
  - assigned_support_user_id
  - requester_role
- Busqueda por id/subject seguro.
- Paginacion/cursor.
- Split view de detalle.

## Detalle

Debe mostrar:

- metadata del ticket
- requester enmascarado segun rol
- recurso asociado: order/ad/credit_purchase/dispute existente si aplica
- mensajes
- eventos
- adjuntos con metadata segura
- assignee
- status y priority

## Acciones

Segun RBAC:

- responder
- asignar
- escalar
- resolver
- cerrar
- abrir adjunto mediante signed URL corta

Acciones con reason obligatorio:

- escalar
- resolver
- cerrar
- cambiar assignee cuando el contrato de API lo requiera

## No debe permitir

- resolver disputa formal
- crear disputa formal desde soporte
- cambiar estados de orden
- mover creditos
- cambiar anuncios
- mutar usuarios o access links
- exportar datos sensibles
- mostrar `storage_path`, signed URLs persistidas, tokens, secretos, datos bancarios completos o cuerpos completos en audit

## Estados

- loading
- empty
- error
- forbidden
- offline/retry
- success after mutation

## Audit

Toda accion admin/support genera eventos de soporte. Abrir adjunto genera `support_attachment_viewed`.
