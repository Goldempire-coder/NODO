# ORDER_LIFECYCLE_MASTER.md

## Slice 14 - Soporte no cambia lifecycle

Los tickets de soporte general, soporte por orden y soporte negocio no cambian `orders.status`.

Chat operativo por orden no es disputa formal.

Solo el flujo formal de disputa puede cambiar una orden a `disputed` o ejecutar efectos de resolucion segun `DISPUTE_RESOLUTION_MASTER.md` y slice autorizado.

Soporte por orden de `slice_20B_support_ticket_center` no cambia `orders.status`, no consume/libera creditos, no cambia `ads.status` y no crea disputa formal.

Este documento gobierna estados, tiempos, cancelaciones, disputas, creditos y anuncios asociados a una orden.

## Estados oficiales

- created
- waiting_payment
- payment_reported
- payment_rejected
- payment_confirmed
- delivered
- completed
- cancelled
- disputed

## completion_reason

- manual_confirmed
- auto_completed_after_24h
- admin_resolved

## cancel_reason

- payment_not_reported_in_time
- remitter_cancelled_before_payment
- admin_cancelled

## dispute_reason

- business_no_payment_confirmation
- business_confirmed_payment_but_not_delivered
- payment_mobile_not_received
- amount_incorrect
- wrong_receiver_data
- other

## Reglas base

- Toda orden congela tasa, monto, negocio, metodo e instrucciones en snapshot.
- `POST /api/v1/orders` persiste la orden directamente como `waiting_payment`.
- `created` se permite solo como evento/audit/state event de creacion, no como estado persistente final del endpoint de creacion.
- Toda transicion pasa por state machine.
- Auto-cierre a completed usa `completion_reason`, no estado nuevo.
- Click al anuncio no crea orden, no cambia estado y no afecta creditos.
- Crear orden pone el anuncio/disponibilidad en hold operativo.
- Los creditos del anuncio ya estan bloqueados desde publicacion.
- Los creditos se consumen cuando el negocio confirma pago recibido o cuando el anuncio llega a 7 dias sin venta confirmada.
- Si la orden expira o se cancela antes de pago confirmado y el anuncio aun no vencio, el anuncio vuelve activo con el credito original bloqueado.

## 1. Cliente crea orden pero no marca Ya pague

Estado:

```txt
waiting_payment
```

Tiempo:

```txt
30 minutos
+ 15 minutos de extension una sola vez
maximo 45 minutos
```

Si no marca `Ya pague`:

```txt
order.status = cancelled
cancel_reason = payment_not_reported_in_time
ad.status = active
credits = keep original ad hold
```

Resultado:

- El negocio no pierde creditos por esa orden fallida.
- El anuncio vuelve al catalogo si no vencio.
- Si el anuncio ya cumplio 7 dias, se archiva y consume el credito.
- Se registra audit event.
- Se notifica al remitente.

En slice 04, la expiracion masiva queda para `slice_10_jobs_notifications`; sin embargo, la lectura o mutacion de una orden `waiting_payment` vencida debe materializar pasivamente la cancelacion, restaurar disponibilidad si el anuncio sigue vivo, consumir el credito si el anuncio ya llego a 7 dias, y auditar el cambio.

## 2. Cliente marca Ya pague pero el negocio no confirma

Estado:

```txt
payment_reported
```

Tiempo:

```txt
2 horas para respuesta normal del negocio
6 horas limite fuerte
```

A las 2 horas:

```txt
bot recuerda al negocio
admin/support recibe warning si es negocio nuevo o de riesgo
```

A las 6 horas sin respuesta:

```txt
order.status = disputed
dispute_reason = business_no_payment_confirmation
ad.status = in_order
credits = still_blocked
```

Resultado:

- El anuncio no vuelve activo.
- Los creditos no se liberan todavia.
- La orden pasa a revision/disputa.
- Se conserva evidencia del pago reportado.
- En `slice_05_payment_instructions_reports`, reportar pago solo mueve `waiting_payment -> payment_reported`.
- Reportar pago no confirma recepcion del negocio.
- Reportar pago no consume creditos.
- Reportar pago no entrega pago movil.
- Reportar pago no completa la orden.
- Despues de `payment_reported`, `ad.status` permanece `in_order` y los creditos siguen bloqueados.
- `payment_reported` no se autocancela por el deadline de `waiting_payment`; la advertencia/escalamiento masivo queda para `slice_10_jobs_notifications`.

## 3. Negocio confirma pago recibido pero no marca pago movil enviado

Estado:

```txt
payment_confirmed
```

Tiempo:

```txt
30 minutos objetivo
2 horas limite fuerte
```

A los 30 minutos:

```txt
bot recuerda al negocio enviar pago movil
```

A las 2 horas sin marcar entregado:

```txt
order.status = disputed
dispute_reason = business_confirmed_payment_but_not_delivered
business.risk_level = under_review si se repite
```

Resultado:

- Los creditos ya estan consumidos porque el negocio confirmo pago recibido.
- El anuncio pasa a `archived` porque ya cumplio su funcion de publicacion.
- La orden sigue viva para entrega, disputa o cierre futuro.
- El caso queda en disputa si no entrega.
- Riesgo interno del negocio aumenta si se repite.
- `under_review` no cambia `verification_status`; es `risk_level`.

## 3.1 Negocio rechaza reporte de pago

Estado:

```txt
payment_rejected
```

Transicion canonica:

```txt
payment_reported -> payment_rejected
```

Reglas:

- El rechazo requiere reason.
- Se actualiza `payment_reports.status = rejected`.
- Se registra `order_state_events`.
- Se audita `payment_report_rejected`.
- No se consume creditos.
- Los creditos siguen bloqueados.
- `ad.status` sigue `in_order`.
- El anuncio no vuelve automaticamente al marketplace.
- La orden no vuelve automaticamente a `waiting_payment`.
- Correccion de reporte, soporte o disputa quedan para slice futuro.

Motivo:

- El cliente afirmo que pago.
- Si el negocio rechaza, debe quedar trazabilidad antes de reabrir, corregir o disputar.
- No se debe tratar como abandono simple de pago.

## 4. Negocio marca pago movil enviado pero cliente no confirma

Estado:

```txt
delivered
```

Tiempo:

```txt
24 horas
```

Recordatorios:

```txt
al momento de entrega
a las 12 horas
a las 23 horas
```

Mensaje obligatorio:

```txt
El negocio marco el pago movil como enviado. Si tu receptor no recibio, abre disputa antes de que la orden cierre automaticamente.
```

Si el cliente no confirma ni abre disputa:

```txt
order.status = completed
completion_reason = auto_completed_after_24h
```

Nota de scope:

- Slice 07 permite abrir disputa desde `delivered`.
- Slice 07 no construye confirmacion de recibido del remitente, completion, rating ni auto-complete.
- La confirmacion del remitente y el auto-complete pertenecen a slice futuro.

## Tabla final de tiempos

| Estado | Problema | Tiempo | Resultado |
| --- | --- | --- | --- |
| waiting_payment | Cliente no reporta pago | 30 min + 15 min extension | cancelled; anuncio vuelve activo con credito bloqueado si no vencio; si llego a 7 dias, archived + ledger `expire` |
| payment_reported | Cliente dice que pago, negocio no responde | 2h warning / 6h disputa | disputed, ad.status = in_order, creditos siguen bloqueados |
| payment_rejected | Negocio rechaza reporte de pago | accion manual futura | creditos siguen bloqueados, ad.status = in_order |
| payment_confirmed | Negocio recibio pago, pero no entrega pago movil | 30 min warning / 2h disputa | disputed, ad.status = archived, creditos consumidos, negocio bajo revision si se repite |
| delivered | Negocio marco pago movil enviado, cliente no confirma | 24h | completed, completion_reason = auto_completed_after_24h |

## Regla simple

```txt
Si el cliente no pago/reporto a tiempo:
se cancela; el anuncio vuelve activo si sigue dentro de sus 7 dias.

Si el anuncio llega a 7 dias sin venta:
se archiva y consume el credito.

Si el cliente reporto pago:
no se cancela automatico; pasa a disputa si el negocio no responde.

Si el negocio confirmo pago:
debe entregar rapido; si no, disputa.

Si el negocio entrego y el cliente no responde:
se cierra automatico en 24h si no hay disputa.
```

## Job obligatorio

Debe existir un job llamado:

```txt
expire_and_escalate_orders
```

Este job revisa cada pocos minutos que ordenes vencieron, cuales deben recordarse y cuales deben pasar a disputa.

## Slice 07 manual dispute opening

Slice 07 puede abrir disputa manual desde:

- `payment_reported`
- `payment_rejected`
- `payment_confirmed`
- `delivered`

Al abrir disputa:

```txt
orders.status = disputed
disputes.previous_order_status = estado anterior
disputes.status = open
```

Efectos:

- Si venia de `payment_reported`: creditos siguen bloqueados y `ad.status = in_order`.
- Si venia de `payment_rejected`: creditos siguen bloqueados y `ad.status = in_order`.
- Si venia de `payment_confirmed`: creditos ya consumidos y `ad.status = archived`.
- Si venia de `delivered`: creditos ya consumidos y `ad.status = archived`.

Slice 07 no resuelve disputas admin ni mueve creditos/anuncios por resolucion.

## Slice 09 admin dispute resolution

Slice 09 puede resolver disputas admin mediante:

```txt
POST /api/v1/admin/disputes/{id}/resolve
```

Precondiciones:

- `orders.status = disputed`.
- `disputes.status in ('open', 'in_review')`.
- actor `admin` o `super_admin`.
- `reason` e `Idempotency-Key` obligatorios.

Transiciones permitidas por `resolution_type`:

| resolution_type | order result |
| --- | --- |
| remitter_favored | `cancelled`, `cancel_reason = admin_cancelled` |
| business_favored | `completed`, `completion_reason = admin_resolved` |
| cancelled | `cancelled`, `cancel_reason = admin_cancelled` |
| completed | `completed`, `completion_reason = admin_resolved` |
| keep_under_review | permanece `disputed` y `disputes.status = in_review` |

Los efectos de creditos y anuncio por resolucion se definen en
`DISPUTE_RESOLUTION_MASTER.md` y `CREDITS_AND_BILLING_MASTER.md`.

NODO registra la decision operativa; no recibe, retiene, transfiere ni garantiza
fondos.
