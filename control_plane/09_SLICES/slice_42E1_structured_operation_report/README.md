# Slice 42E1 Structured Operation Report

Estado: `IMPLEMENTED_LOCAL_VALIDATOR_REVIEW_REQUIRED`

## Alcance

El cliente propietario crea un reporte estructurado desde el detalle de una
orden reportable mediante:

```text
POST /api/v1/orders/{order_id}/operation-report
```

El backend deriva `business_id` desde la orden. El payload acepta solo
`category` y `message`, exige `Idempotency-Key` y rechaza campos extra.

Estados reportables: `payment_confirmed`, `delivered`, `completed`,
`payment_rejected`, `disputed` y `cancelled`.

## Persistencia y privacidad

- `support_tickets.report_kind = structured_operation_report` distingue el
  ticket durable de soporte generico.
- Solo puede existir un reporte estructurado activo por orden.
- Orden inexistente y ajena responden `ORDER_NOT_FOUND`.
- El negocio no puede listar ni abrir el reporte aunque el ticket conserve su
  `business_id` interno.
- La respuesta usa `private, no-store` y no expone `report_kind`.
- No existe entrada desde chat.

## Fuera de alcance

42E1 por si solo no creaba hold. El slice posterior 42F1 extiende el mismo
endpoint para crear el hold durable durante una pausa activa, sin alterar orden,
anuncio, disputa, credito, capacidad, pago, rating o reputacion publica.
Telegram permanece fuera de alcance hasta 42F2.

No autoriza deploy, staging, produccion ni `READY_FOR_REAL_USE`.
