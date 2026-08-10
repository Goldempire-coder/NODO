# STATE_CONTRACT.md

Comportamiento oficial de estados para `slice_06_business_order_ops`.

## Transiciones permitidas

```txt
payment_reported -> payment_confirmed
payment_reported -> disputed
payment_confirmed -> delivered
```

## Problema con pago reportado

La decision C0 sustituye el rechazo directo por:

```txt
payment_reported -> disputed
dispute.reason = payment_not_received_or_incomplete
```

No se devuelve a `waiting_payment`, no se cierra y no cambia unilateralmente el
reporte a `rejected`.

Motivo:

- El cliente afirmo que pago.
- Si el negocio no reconoce el pago, debe abrir una disputa investigable.
- Debe quedar trazabilidad atomica de disputa, orden, eventos y auditoria.
- `payment_rejected` queda solo para filas historicas y recuperacion Admin.

## Confirmar pago

`confirm-payment`:

- requiere `orders.status = payment_reported`.
- requiere `payment_reports.status = submitted`.
- setea `orders.status = payment_confirmed`.
- setea `payment_confirmed_at`.
- setea `delivery_warning_at = now + 30 minutes`.
- setea `delivery_deadline_at = now + 2 hours`.
- setea `payment_reports.status = accepted`.
- consume creditos bloqueados exactamente una vez.
- setea `ad.status = archived`.
- crea `order_state_events`.
- audita `payment_confirmed`, `credits_consumed` y `ad_archived`.
- no marca `delivered`.
- no completa orden.
- no abre disputa.
- la orden sigue viva para entrega, disputa o cierre futuro.
- el anuncio no vuelve al marketplace.

## Reportar problema con pago

`POST /api/v1/orders/{id}/disputes`:

- requiere `orders.status = payment_reported`.
- requiere `payment_reports.status = submitted`.
- requiere `reason = payment_not_received_or_incomplete`.
- setea `orders.status = disputed` y crea disputa `open` atomicamente.
- mantiene `payment_reports.status = submitted` hasta resolucion Admin.
- crea eventos de orden/disputa y audita `dispute_opened`.
- no consume creditos.
- mantiene creditos bloqueados.
- mantiene `ad.status = in_order`.
- no libera anuncio.
- no devuelve orden al marketplace.

`reject-payment-report` queda como endpoint legacy y debe responder
`PAYMENT_REJECTION_NOT_ALLOWED` sin efectos.

## Marcar entregado

`mark-delivered`:

- requiere `orders.status = payment_confirmed`.
- setea `orders.status = delivered`.
- setea `delivered_at`.
- setea `auto_complete_warning_12h_at = now + 12 hours`.
- setea `auto_complete_warning_23h_at = now + 23 hours`.
- setea `auto_complete_at = now + 24 hours`.
- crea `order_state_events`.
- audita `order_delivered`.
- no completa orden.
- no confirma recepcion del cliente.
- no abre chat/disputa.
- no consume creditos aqui.

## Reglas

- No usar estados fuera de `04_DATA/ENUMS_AND_STATUS_MASTER.md`.
- Todas las transiciones pasan por state machine/service.
- Toda transicion valida actor, ownership, estado actual y siguiente estado permitido.
- Toda transicion sensible genera audit log y state event.
- Si aparece conflicto de estado, detener con `BLOCKED_BY_CONTRACT_CONFLICT`.
