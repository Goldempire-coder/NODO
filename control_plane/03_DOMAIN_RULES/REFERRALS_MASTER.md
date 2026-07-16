# REFERRALS_MASTER.md

Contrato canonico de referrals para NODO.

## Decision canonica

Slice 08 usa dos tablas activas:

- `referral_codes`
- `referral_events`

La tabla singular `referrals` queda legacy/no valida para nuevas migraciones y
contratos activos.

## Modelo funcional

- Cada negocio aprobado puede tener un codigo de referido unico.
- El codigo se genera de forma idempotente al aprobar el negocio o al primer
  acceso a `GET /api/v1/business/referrals`.
- Un negocio puede aplicar un codigo de referido una sola vez antes de recibir
  bonus propio o antes de su primera compra calificable de creditos.
- Self-referral esta prohibido.
- Un mismo referred_business_id no puede generar mas de un bonus activo.
- Un mismo credit_purchase no puede generar mas de un referral bonus.

## Bonus

- Bonus por referido: 1 credito publicitario.
- Cap por negocio referrer: 20 creditos por referrals en MVP.
- El bonus se acredita cuando el negocio referido:
  - esta `business.verification_status = approved`
  - tiene su primera compra calificable de creditos
  - no es self-referral
  - no excede el cap
- La acreditacion escribe `credits_ledger.type = referral_bonus`.

Compra calificable:

- `credit_purchases.status = approved` para Stripe/manual legacy.
- `credit_purchases.status = credited` para Base USDC on-chain.
- En ambos casos debe existir `credits_ledger.type = purchase` exact-once con `related_credit_purchase_id = credit_purchases.id`.

Una compra con status `verified`, `detected`, `pending_onchain_confirmation`, `under_review`, `expired`, `rejected` o `verification_failed` no califica referral.

## Ledger

`referral_bonus` debe incluir:

- business_id = referrer_business_id
- amount = bonus credits
- related_referral_id = referral_events.id
- related_credit_purchase_id = credit_purchases.id
- reason = referral_bonus_first_qualifying_purchase
- source = referral_events
- reference_type = referral_event
- reference_id = referral_events.id
- created_by = system/admin actor segun origen

## Estados

`referral_code.status`:

- active
- disabled

`referral_event.status`:

- pending
- approved
- rewarded
- rejected

## API

- `GET /api/v1/business/referrals`
- `POST /api/v1/business/referrals/apply`

## RBAC

- `business_owner` ve su codigo, eventos y cap.
- `business_owner` puede aplicar un codigo a su propio negocio cuando el
  estado lo permite.
- `admin/super_admin` puede ver eventos en pantallas admin futuras.
- `support` es read-only si un contrato admin futuro lo expone.

## Auditoria

Eventos:

- referral_code_created
- referral_code_applied
- referral_bonus_awarded
- referral_rejected

## Errores

- REFERRAL_NOT_ALLOWED
- REFERRAL_ALREADY_USED
- REFERRAL_CODE_NOT_FOUND
- REFERRAL_CAP_REACHED

## Prohibido

- Self-referral.
- Doble bonus por el mismo referred_business_id.
- Doble bonus por la misma compra calificable.
- Bonus que haga wallet inconsistente.
- Prometer ganancias monetarias, fondos protegidos o garantia de remesas.
