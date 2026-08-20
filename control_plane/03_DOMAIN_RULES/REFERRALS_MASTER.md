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
- El solicitante escribe el codigo una sola vez durante Telegram Business Intake.
- Backend normaliza el codigo con `trim + uppercase` y deriva el negocio referente.
- Self-referral esta prohibido.
- Un mismo referred_business_id no puede generar mas de un bonus activo.
- Las compras de creditos no generan ni duplican referral bonus.

## Bonus

- Bonus por referido: 5 creditos publicitarios para el negocio referente.
- El negocio referido no recibe creditos por usar el codigo.
- Cap por negocio referrer: 20 creditos por referrals en MVP.
- El bonus se acredita en la transaccion que deja al negocio referido con
  `business.verification_status = approved` por decision Admin.
- La acreditacion:
  - usa `min(5, 20 - referral_credits_earned)`
  - no es self-referral
  - no excede el cap
- La acreditacion escribe `credits_ledger.type = referral_bonus`.
- Replay o concurrencia de aprobacion no crea otro evento, ledger ni credito.
- Un evento legacy `pending` se finaliza en esa misma aprobacion si sigue siendo
  elegible; no se descarta como procesado solo por existir.
- Un evento legacy `rewarded` o `rejected` es terminal y nunca vuelve a acreditar.

## Ledger

`referral_bonus` debe incluir:

- business_id = referrer_business_id
- amount = bonus credits
- related_referral_id = referral_events.id
- related_credit_purchase_id = null
- reason = referral_bonus_business_approval
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
- `POST /api/v1/business/referrals/apply` queda legacy para compatibilidad y no
  es la entrada canonica del flujo nuevo.

## RBAC

- `business_owner` ve su codigo, eventos y cap.
- El negocio referido no aplica codigos desde la App Negocio despues de aprobado.
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
- Doble bonus por replay o concurrencia de aprobacion.
- Bonus que haga wallet inconsistente.
- Prometer ganancias monetarias, fondos protegidos o garantia de remesas.
