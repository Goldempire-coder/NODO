# Slice 48A Security Contract

Estado: READY_FOR_VALIDATOR_REVIEW

## Autorizacion

- El backend valida ownership de la orden.
- Cliente, negocio, Admin o terceros no pueden usar este endpoint para cancelar
  una orden ajena.
- `Idempotency-Key` sigue siendo obligatorio.
- `payment_reported` y estados posteriores no aceptan cancelacion libre.

## Datos Permitidos

- `order_id`
- codigo publico de orden
- estado `cancelled`
- motivo allowlist
- `request_id`, `correlation_id` y `operation_id`

## Datos Prohibidos En Notificacion, Logs Y Auditoria

- instrucciones completas de pago;
- `account_value`;
- datos completos del receptor;
- tokens, PIN o secretos;
- `storage_path` o signed URLs;
- comprobantes o cuerpos privados.

## Lenguaje Seguro

Permitido:

`Cancelada antes de reportar pago.`

Prohibido:

- `No se movio dinero.`
- `El negocio tuvo la culpa.`
- `El cliente no pago.`
