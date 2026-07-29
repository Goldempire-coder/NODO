# Slice 48A API Contract

Estado: READY_FOR_VALIDATOR_REVIEW

## Endpoint Reutilizado

```txt
POST /api/v1/orders/{order_id}/cancel
```

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "business_unavailable",
  "payment_not_sent_confirmed": true
}
```

`reason` solo admite:

- `business_not_responding`
- `business_unavailable`
- `customer_mistake`
- `choose_another_business`

Para compatibilidad con el endpoint existente, omitir el payload usa
`choose_another_business`. La Mini App Cliente siempre envia motivo y
confirmacion explicitos.
`payment_not_sent_confirmed` debe ser booleano real; texto como `"true"` no
cuenta como confirmacion.

## Reglas

- Solo el remitente propietario.
- Solo `waiting_payment`.
- Si existe reporte de pago, la cancelacion libre se rechaza.
- Si las instrucciones fueron reveladas, se requiere
  `payment_not_sent_confirmed = true`.
- La confirmacion es una declaracion del cliente; NODO no valida ni afirma que
  no hubo transferencia fuera del sistema.
- La orden queda `cancelled` con
  `cancel_reason = remitter_cancelled_before_payment`.
- El state event guarda solo el codigo allowlist.
- El replay idempotente no duplica liberacion ni notificacion.

Error adicional:

```txt
ORDER_PAYMENT_NOT_SENT_CONFIRMATION_REQUIRED -> 409
```

## Notificacion

La cancelacion manual encola una sola notificacion
`order_cancelled_payment_not_reported` para el owner del negocio, marcada como
canal Telegram inmediato y superficie `business_mini_app`.

El mensaje no contiene instrucciones de pago, cuenta, receptor, documentos,
evidencia ni payload privado.
