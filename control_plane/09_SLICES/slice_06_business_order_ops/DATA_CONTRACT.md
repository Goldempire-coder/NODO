# DATA_CONTRACT.md

Datos autoritativos tocados por `slice_06_business_order_ops`:

- `orders`
- `payment_reports`
- `ads`
- `order_state_events`
- `credits_ledger`
- `credit_wallets`
- `audit_logs`

## Orders

El slice puede actualizar:

- `status`
- `payment_confirmed_at`
- `delivery_warning_at`
- `delivery_deadline_at`
- `delivered_at`
- `auto_complete_warning_12h_at`
- `auto_complete_warning_23h_at`
- `auto_complete_at`
- `updated_at`

No puede modificar snapshots monetarios, instrucciones privadas, `amount_usd`, `rate_snapshot`, `amount_bs_calculated`, `business_id`, `ad_id` ni `remitter_user_id`.

## Payment reports

- Confirmar pago cambia `payment_reports.status` de `submitted` a `accepted`.
- `rejected` se conserva para historial. Reportar problema con pago mantiene
  `submitted` hasta resolucion Admin.
- Slice 06 no crea nuevos reportes del remitente.
- Slice 06 no corrige reportes; `corrected` queda para flujo futuro.

## Ads

- Confirmar pago recibido setea `ads.status = archived`.
- El anuncio ya cumplio su funcion de publicacion y no vuelve al marketplace.
- La orden sigue viva para entrega, disputa o cierre futuro.
- Abrir disputa por problema con pago mantiene `ads.status = in_order`.

## Credits

Confirmar pago consume creditos bloqueados del anuncio:

```txt
credit_wallets.blocked_credits -= ads.required_credits
credit_wallets.consumed_credits += ads.required_credits
```

Ledger `consume` obligatorio:

```txt
business_id = orders.business_id
type = consume
amount = ads.required_credits
related_ad_id = orders.ad_id
related_order_id = orders.id
reason = business_confirmed_payment_received
source = orders
reference_type = order
reference_id = orders.id
created_by = business owner id
```

## Anti doble consumo

- `credit_wallets.blocked_credits` nunca puede quedar negativo.
- Debe detectarse ledger `consume` existente por `related_order_id/reference_id`.
- El consumo debe ser transaccional con `orders.status = payment_confirmed` y `payment_reports.status = accepted`.
- El archivado del anuncio a `archived` debe ser transaccional con `orders.status = payment_confirmed`, `payment_reports.status = accepted`, wallet y ledger `consume`.
- Si no existe hold valido, devolver `CREDIT_HOLD_NOT_FOUND`.
- Si ya se consumio para la orden, devolver resultado idempotente o `CREDIT_ALREADY_CONSUMED` segun key/estado.

## Rules

- Usar migraciones, no ediciones manuales de DB.
- Agregar constraints e indices para queries calientes.
- Nunca guardar dinero/tasa como float.
- Campos sensibles deben mostrarse enmascarados cuando no sean estrictamente necesarios.
- Cada cambio de estado debe ser trazable por `audit_logs` y `order_state_events`.
