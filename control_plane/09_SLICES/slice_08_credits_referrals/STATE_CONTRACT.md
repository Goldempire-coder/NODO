# STATE_CONTRACT.md

## credit_purchase.status

Estados oficiales:

- created
- pending_payment
- pending_manual_review
- paid
- approved
- rejected
- failed
- expired

Transiciones:

- created -> pending_payment
- created -> pending_manual_review
- pending_payment -> paid
- paid -> approved
- pending_payment -> failed
- pending_payment -> expired
- pending_manual_review -> approved
- pending_manual_review -> rejected
- pending_manual_review -> expired

Reglas:

- Stripe checkout crea `pending_payment`.
- Stripe webhook firmado mueve `pending_payment -> paid -> approved`.
- Redirect frontend no cambia estado ni acredita.
- Pago manual crea `pending_manual_review`.
- Admin approve mueve `pending_manual_review -> approved`.
- Admin reject mueve `pending_manual_review -> rejected`.
- `approved`, `rejected`, `failed` y `expired` son terminales para acreditacion.
- Reintentos idempotentes devuelven el mismo resultado si payload coincide.
- Payload distinto con misma key devuelve `IDEMPOTENCY_PAYLOAD_MISMATCH`.

## Wallet/ledger

- `credit_wallets` y `credits_ledger` son fuente de verdad.
- Ledger es append-only.
- Acreditar wallet requiere ledger:
  - purchase
  - referral_bonus
  - admin_adjustment
- Founder es solo historial: no acredita wallet ni exime del hold. Carlos asigna creditos mediante el ajuste administrativo normal (decision Owner 2026-09-29).
- No se permiten balances negativos.
- No se permite doble acreditacion por la misma compra/referral/admin action.

## Reglas preservadas

- Publicar anuncio bloquea creditos.
- Crear orden no consume creditos.
- Reportar pago no consume creditos.
- Confirmar pago recibido consume creditos.
- Cancel/expiry antes de confirmacion libera segun contrato existente.
