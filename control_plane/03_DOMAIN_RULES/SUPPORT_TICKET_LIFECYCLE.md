# SUPPORT_TICKET_LIFECYCLE.md

## Estados

- `open`
- `waiting_user`
- `waiting_support`
- `escalated`
- `resolved`
- `closed`

## Scopes

- `client_general`
- `client_order`
- `business_general`
- `business_order`
- `business_ad`
- `business_credit`
- `admin_internal`

## Categorias

- `technical_issue`
- `account_access`
- `order_help`
- `payment_report_help`
- `business_access`
- `credits_help`
- `suspicious_activity`
- `other`

## Transiciones

- `open -> waiting_support`
- `waiting_support -> waiting_user`
- `waiting_user -> waiting_support`
- `waiting_support -> escalated`
- `escalated -> waiting_support`
- `waiting_support -> resolved`
- `escalated -> resolved`
- `resolved -> closed`

## Reglas

- Soporte general no cambia estados de orden.
- Soporte por orden puede enlazarse a `orders.id`, pero no muta orden por si solo.
- Resolver/cerrar ticket no resuelve disputa formal.
- Adjuntos usan storage privado.
- En 20B, escalar no crea disputa formal. Puede vincular metadata a disputa existente solo si el actor puede verla.
- Soporte no mueve creditos, no cambia anuncios, no modifica pagos y no toca access links.
- En 20C, asignar tickets a staff requiere permiso activo y scope compatible.
- Staff con scope `assigned_only` no puede ver ni responder tickets no asignados.
- Ver adjuntos privados requiere permiso `view_support_attachment`, reason y audit.
- Revocar/suspender staff debe impedir nuevas acciones de soporte inmediatamente sin modificar el historial del ticket.
