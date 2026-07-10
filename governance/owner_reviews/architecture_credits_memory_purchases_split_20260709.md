# Architecture Review - Credits Memory Purchases Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de compras in-memory del repositorio de creditos usado en tests/runtime local.

No se cambiaron reglas de compra Stripe, compra manual, aprobacion, rechazo, idempotencia, wallet, ledger, referral bonus, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/credits/memory_purchases.py`
- `apps/api/app/modules/credits/memory_repository.py`

## Cambio realizado

- Se creo `InMemoryCreditPurchaseStore`.
- `InMemoryCreditRepository` conserva la misma interfaz publica y delega compras al store.
- El store maneja:
  - `create_stripe_purchase`
  - `create_manual_purchase`
  - `get_purchase`
  - `find_purchase_by_checkout_session`
  - `stripe_event_processed`
  - `approve_purchase`
  - `reject_purchase`
  - `list_purchases`
- La busqueda de ledger ya aprobado se pasa como callback explicito, sin introspeccion ni acoplamiento oculto.

## Medicion despues del corte

- `apps/api/app/modules/credits/memory_repository.py`: 234 lineas
- `apps/api/app/modules/credits/memory_purchases.py`: 151 lineas

Antes del corte, `memory_repository.py` tenia 298 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`memory_repository.py` todavia contiene referrals, wallet helpers y referral bonus. Ya no contiene la logica de compras.

## Siguiente corte recomendado

Separar referrals in-memory para alinear con `postgres_referrals.py`.
