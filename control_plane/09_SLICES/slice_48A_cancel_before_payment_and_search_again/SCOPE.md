# Slice 48A Scope

Estado: READY_FOR_VALIDATOR_REVIEW

## Incluido

- Contrato de cancelacion antes de reporte de pago.
- Motivos de cancelacion allowlist.
- Confirmacion explicita de que el cliente no envio el pago.
- Retorno a marketplace con el monto de la orden cancelada.
- Invalidacion de cache local antes de la nueva busqueda.
- Notificacion segura al owner del negocio.
- Copy neutral en Admin.
- Pruebas backend, frontend estaticas y de privacidad.

## Excluido

- Nuevos endpoints o estados de orden.
- Cancelacion por el negocio.
- Cambios al lifecycle posterior a `payment_reported`.
- Penalizaciones, reputacion o reglas antiabuso automaticas.
- Migraciones, dependencias o infraestructura nueva.
- Pagos, Base USDC, Zelle, creditos y soporte general.
