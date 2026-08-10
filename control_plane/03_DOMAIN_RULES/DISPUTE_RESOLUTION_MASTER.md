# DISPUTE_RESOLUTION_MASTER.md

## Slice 14 - Soporte vs disputa

Un ticket de soporte puede escalar a disputa solo cuando el contrato de disputa y ownership lo permitan.

En `slice_20B_support_ticket_center`, soporte no crea disputas nuevas ni resuelve disputas. Solo puede marcar un ticket como `escalated` o vincular metadata a una disputa existente que el actor pueda ver. Abrir o resolver disputa formal sigue gobernado por los endpoints de disputa existentes.

Soporte no resuelve disputas por si mismo. Resolver disputa sigue siendo accion admin/super_admin gobernada por el slice y API de disputas correspondiente.

Chat operativo, soporte general y soporte por orden no son equivalentes a `disputes`.

Disputas simples para MVP. Una disputa existe para revisar evidencia y proteger confianza cuando una orden no puede avanzar automaticamente.

## Razones oficiales

- business_no_payment_confirmation
- payment_not_received_or_incomplete
- business_confirmed_payment_but_not_delivered
- payment_mobile_not_received
- amount_incorrect
- wrong_receiver_data
- other

`payment_not_received_or_incomplete` se usa para el problema Zelle/USDT abierto
desde `payment_reported`. `payment_mobile_not_received` queda reservado para el
flujo de entrega de Pago Movil posterior a la confirmacion del pago.

## Apertura automatica por timers

### payment_reported sin respuesta del negocio

Si el cliente marco `Ya pague` y el negocio no confirma ni abre una disputa en
6 horas:

```txt
order.status = disputed
dispute_reason = business_no_payment_confirmation
ad.status = in_order
credits = still_blocked
```

No liberar creditos todavia porque puede existir dinero enviado.

### payment_confirmed sin entrega

Si el negocio confirmo pago recibido y no marca pago movil enviado en 2 horas:

```txt
order.status = disputed
dispute_reason = business_confirmed_payment_but_not_delivered
credits = consumed
```

El negocio queda bajo observacion/riesgo si el patron se repite.

## Apertura manual por usuario

El remitente puede abrir disputa cuando:

- reporto pago y el negocio no responde.
- el negocio marco entregado pero el receptor no recibio.
- el monto recibido es incorrecto.
- los datos usados fueron incorrectos.

## Estado canonico de disputa

`disputes.status`:

- open
- in_review
- resolved
- cancelled

Transiciones canonicas:

- open -> in_review
- open -> resolved
- in_review -> resolved
- open -> cancelled

Slice 07 solo crea disputas `open` y guarda `previous_order_status`.

Al abrir disputa:

- `orders.status = disputed`.
- `orders.dispute_reason = reason`.
- `disputes.previous_order_status` guarda el estado anterior.
- Se crea `dispute_events.event_type = dispute_opened`.
- Se audita `dispute_opened`.

Efectos por origen:

- Desde `payment_reported`: creditos siguen bloqueados, `ad.status = in_order`.
- Desde `payment_rejected`: creditos siguen bloqueados, `ad.status = in_order`.
- Desde `payment_confirmed`: creditos ya consumidos, `ad.status = archived`.
- Desde `delivered`: creditos ya consumidos, `ad.status = archived`.

## Resolucion admin

La resolucion admin completa no pertenece a `slice_07_chat_disputes`.

Pertenece a `slice_09_admin_console` y solo puede construirse usando:

```txt
POST /api/v1/admin/disputes/{id}/resolve
```

Admin revisa:

- snapshot de orden.
- evidencia de pago.
- chat.
- tiempos.
- historial del negocio.
- historial del remitente.

Admin puede aplicar solo estos `resolution_type` canonicos:

- remitter_favored
- business_favored
- cancelled
- completed
- keep_under_review

Toda resolucion requiere:

- actor `admin` o `super_admin` activo.
- `Idempotency-Key`.
- `reason` obligatorio.
- `disputes.status in ('open', 'in_review')`.
- `orders.status = disputed`.
- `dispute_events`.
- audit log.

`support` puede ver disputas segun RBAC, pero no resolver.

## Efectos canonicos por resolution_type

| resolution_type | disputes.status | orders.status | credits | credits_ledger | ad.status |
| --- | --- | --- | --- | --- | --- |
| remitter_favored | resolved | cancelled con `cancel_reason = admin_cancelled` | si venia de `payment_reported` o `payment_rejected`, consumir creditos bloqueados; si ya estaban consumidos, no mover de nuevo | `consume` con `reason = admin_dispute_resolution_consume` cuando aplique | archived |
| business_favored | resolved | completed con `completion_reason = admin_resolved` | si venia de `payment_reported` o `payment_rejected`, consumir creditos bloqueados; si ya estaban consumidos, no mover de nuevo | `consume` con `reason = admin_dispute_resolution_consume` cuando aplique | archived |
| cancelled | cancelled | cancelled con `cancel_reason = admin_cancelled` | si venia de `payment_reported` o `payment_rejected`, liberar creditos bloqueados; si ya estaban consumidos, no hacer refund automatico en MVP | `release` con `reason = admin_dispute_resolution_release` cuando aplique | archived |
| completed | resolved | completed con `completion_reason = admin_resolved` | si venia de `payment_reported` o `payment_rejected`, consumir creditos bloqueados; si ya estaban consumidos, no mover de nuevo | `consume` con `reason = admin_dispute_resolution_consume` cuando aplique | archived |
| keep_under_review | in_review | disputed | sin movimiento | none | igual al origen de la disputa |

Reglas de creditos:

- Si `previous_order_status in ('payment_reported', 'payment_rejected')`, los creditos estaban bloqueados.
- Si `previous_order_status in ('payment_confirmed', 'delivered')`, los creditos ya estaban consumidos.
- Nunca puede existir doble `consume` o `release` por la misma resolucion de disputa.
- El wallet nunca puede quedar negativo.
- Todo movimiento de creditos por resolucion admin requiere ledger append-only y audit.

Reglas de anuncio:

- Las resoluciones terminales archivan el anuncio para que no vuelva al marketplace desde una disputa.
- `keep_under_review` mantiene el `ad.status` derivado del origen:
  - `in_order` para disputas originadas en `payment_reported` o `payment_rejected`.
  - `archived` para disputas originadas en `payment_confirmed` o `delivered`.

Notificaciones:

- `dispute_resolved` notifica a las partes sin prometer recuperacion de fondos.
- `keep_under_review` puede notificar revision en curso cuando slice 10 implemente workers/notificaciones.
- Payloads no deben incluir instrucciones completas, `account_value`, `storage_path`, signed URLs, tokens ni secretos.

Regla base de NODO:

NODO no retiene, recibe, transfiere ni garantiza fondos. Resolver disputa
significa registrar una decision operativa/admin dentro de NODO, no mover dinero
real.

## Riesgo interno

`under_review` es un valor de `business.risk_level`, no de `business.verification_status`.

Un negocio puede seguir `verification_status = approved` y estar temporalmente en `risk_level = under_review`.

Solo admin cambia `verification_status` a `suspended` o `blocked` cuando el caso lo amerita.
