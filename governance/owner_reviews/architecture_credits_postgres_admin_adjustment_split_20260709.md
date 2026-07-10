# Architecture Review - Credits Postgres Admin Adjustment Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de la transaccion Postgres de ajuste admin de creditos.

No se cambiaron reglas de ajuste, validacion de balance no negativo, ledger, wallet, permisos, idempotencia, audit events, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/credits/postgres_admin_adjustment.py`
- `apps/api/app/modules/credits/postgres_repository.py`

## Cambio realizado

- Se creo `adjust_wallet_pg`.
- `PostgresCreditRepository.adjust_wallet` mantiene la firma publica y delega al helper.
- El helper conserva:
  - lock de wallet con `for update`
  - creacion de wallet si no existe
  - validacion `CREDIT_BALANCE_INSUFFICIENT`
  - update de `available_credits`
  - incremento de `lifetime_adjusted_credits` solo en add
  - ledger `admin_adjustment`
  - commit de la transaccion

## Medicion despues del corte

- `apps/api/app/modules/credits/postgres_repository.py`: 279 lineas
- `apps/api/app/modules/credits/postgres_admin_adjustment.py`: 58 lineas

Antes de los cortes de creditos, `postgres_repository.py` tenia 491 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q -k "admin_adjustment"`: 1 passed, 6 deselected, 1 warning
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

El repositorio Postgres de creditos ya esta bastante mas pequeno, pero aun contiene bloques de compra/aprobacion:

- `create_stripe_purchase`
- `create_manual_purchase`
- `approve_purchase`
- `reject_purchase`
- `list_purchases`

## Siguiente corte recomendado

Leer `create_stripe_purchase`, `create_manual_purchase`, `reject_purchase` y `list_purchases`. Si estan aislados, moverlos a `postgres_purchases.py` dejando `approve_purchase` en el repositorio principal o en un helper separado.
