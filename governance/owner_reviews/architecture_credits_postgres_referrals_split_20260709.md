# Architecture Review - Credits Postgres Referrals Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de operaciones Postgres de referral code y referral events desde el repositorio principal de creditos.

No se cambiaron reglas de referral, codigos, eventos, cap, bonus, wallet, ledger, compras, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/credits/postgres_referrals.py`
- `apps/api/app/modules/credits/postgres_repository.py`

## Cambio realizado

- Se creo `postgres_referrals.py` con:
  - `get_or_create_referral_code_pg`
  - `apply_referral_code_pg`
  - `list_referral_events_for_business_pg`
- `PostgresCreditRepository` conserva las mismas firmas publicas y delega a los helpers.
- El servicio de creditos no fue modificado en este corte.

## Medicion despues del corte

- `apps/api/app/modules/credits/postgres_repository.py`: 327 lineas
- `apps/api/app/modules/credits/postgres_referrals.py`: 76 lineas

Antes de los cortes de creditos, `postgres_repository.py` tenia 491 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q -k "referral"`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`credits/postgres_repository.py` ya bajo bastante, pero aun contiene:

- wallet
- ledger
- Stripe purchase
- manual purchase
- approve/reject purchase
- admin adjustment

## Siguiente corte recomendado

Leer primero `adjust_wallet`. Es un bloque transaccional admin claro y puede moverse a helper Postgres sin tocar el servicio.
