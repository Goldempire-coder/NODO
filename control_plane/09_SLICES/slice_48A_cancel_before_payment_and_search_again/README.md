# Slice 48A - Cancel Before Payment And Search Again

Estado: READY_FOR_VALIDATOR_REVIEW

## Objetivo

Permitir que el cliente cancele su propia orden mientras sigue en
`waiting_payment`, deje evidencia durable de que la cancelacion ocurrio antes
de reportar pago y vuelva a buscar otro negocio por el mismo monto.

NODO no afirma que no hubo una transferencia. El sistema solo puede afirmar
que la orden fue cancelada antes de que el cliente reportara pago en NODO.

## Resultado

- Se conserva `POST /api/v1/orders/{order_id}/cancel`.
- No se crea un estado de orden nuevo.
- La orden termina como `cancelled`.
- `cancel_reason` permanece `remitter_cancelled_before_payment`.
- La capacidad se libera y el anuncio vuelve a estar disponible si sigue vivo.
- El cliente confirma que no envio el pago y elige un motivo acotado.
- La Mini App Cliente ejecuta una busqueda fresca por el mismo monto.
- El owner del negocio recibe un aviso seguro e idempotente.
- Admin ve una explicacion neutral en el detalle de la orden.

## Fuera De Alcance

- Cancelacion libre despues de `payment_reported`.
- Accion de negocio `No puedo atender`.
- Cambios de pagos, creditos, USDC, Zelle, reputacion o soporte.
- Borrado de ordenes, eventos, auditoria o historial.
- Deploy, produccion o infraestructura nueva.
