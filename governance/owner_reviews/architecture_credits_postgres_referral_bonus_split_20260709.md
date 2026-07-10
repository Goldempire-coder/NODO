# Architecture Review - Credits Postgres Referral Bonus Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de la logica transaccional de bonus de referido del repositorio Postgres de creditos.

No se cambiaron reglas de aprobacion de compra, wallet, ledger, referral cap, referral status, Stripe, pagos manuales, admin review, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/credits/postgres_referral_bonus.py`
- `apps/api/app/modules/credits/postgres_repository.py`

## Cambio realizado

- Se creo `postgres_referral_bonus.py` con `grant_referral_bonus_if_eligible_pg`.
- `approve_purchase` sigue controlando la transaccion y pasa el mismo `conn` al helper.
- El helper conserva los mismos locks, queries y updates:
  - busca referral pending
  - evita doble bonus por `related_credit_purchase_id`
  - bloquea negocio referrer
  - bloquea/crea wallet referrer
  - acredita 1 credito de bonus
  - actualiza `referral_credits_earned`
  - marca referral como `rewarded`
  - escribe ledger `referral_bonus`
  - rechaza si cap/referrer invalido

## Medicion despues del corte

- `apps/api/app/modules/credits/postgres_repository.py`: 388 lineas
- `apps/api/app/modules/credits/postgres_referral_bonus.py`: 106 lineas

Antes del corte, `postgres_repository.py` tenia 491 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`credits/postgres_repository.py` sigue siendo grande, pero ya bajo de 491 a 388 lineas. Los siguientes bloques candidatos son:

- `create_manual_purchase`: mezcla `file_assets` y `credit_purchases`.
- `adjust_wallet`: transaccion admin de ajuste.
- `apply_referral_code` y `get_or_create_referral_code`: logica de referrals.

## Siguiente corte recomendado

Leer primero `create_manual_purchase`. Si no hay acoplamiento oculto, mover el insert de `file_assets` a un helper transaccional para dejar la compra manual mas legible sin cambiar la transaccion.
