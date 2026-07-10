# SUPPORT_TICKET_LIFECYCLE.md

## Estados

- `open`
- `waiting_user`
- `waiting_business`
- `waiting_support`
- `escalated`
- `linked_to_dispute`
- `resolved`
- `closed`

## Scopes

- `client_general`
- `order_support`
- `business_general`
- `admin_internal`

## Transiciones

- `open -> waiting_support`
- `waiting_support -> waiting_user`
- `waiting_support -> waiting_business`
- `waiting_user -> waiting_support`
- `waiting_business -> waiting_support`
- `waiting_support -> escalated`
- `escalated -> linked_to_dispute`
- `waiting_support -> resolved`
- `escalated -> resolved`
- `resolved -> closed`

## Reglas

- Soporte general no cambia estados de orden.
- Soporte por orden puede enlazarse a `orders.id`, pero no muta orden por si solo.
- `linked_to_dispute` requiere `dispute_id` y evento auditado.
- Resolver/cerrar ticket no resuelve disputa formal.
- Adjuntos usan storage privado.
