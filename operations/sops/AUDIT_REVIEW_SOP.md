# SOP: Audit Review

SOP_ID: SOP-AUDIT-001
Estado de validacion: NOT VALIDATED

## Proposito

Revisar eventos criticos despues de incidentes o cambios sensibles.

## Eventos a revisar

- `credits_added`
- `onchain_credit_purchase_credited`
- `business_access_linked`
- `business_access_blocked`
- `user_blocked`
- `staff_permissions_updated`
- `support_ticket_escalated`
- `order_created`
- `payment_confirmed`
- `dispute_resolved`

## Procedimiento

1. Abrir Admin Web audit logs.
2. Filtrar por resource type/id.
3. Guardar request IDs.
4. Comparar con estado actual.
5. Adjuntar evidencia al incidente/postmortem.

## Bloqueo

No hay export operacional versionado; si se necesita export, crear slice separado.
