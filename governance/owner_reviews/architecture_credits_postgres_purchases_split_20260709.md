# Architecture Review - Credits Postgres Purchases Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del bloque Postgres de compras de creditos.

No se cambiaron reglas de Stripe, compra manual, aprobacion, rechazo, lock `for update`, estados permitidos, wallet, ledger, referral bonus, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/credits/postgres_purchases.py`
- `apps/api/app/modules/credits/postgres_repository.py`
- `apps/api/tests/test_credits_referrals.py`

## Cambio realizado

- Se creo `postgres_purchases.py` con:
  - `create_stripe_purchase_pg`
  - `create_manual_purchase_pg`
  - `get_purchase_pg`
  - `find_purchase_by_checkout_session_pg`
  - `stripe_event_processed_pg`
  - `approve_purchase_pg`
  - `reject_purchase_pg`
  - `list_purchases_pg`
- `PostgresCreditRepository` conserva las mismas firmas publicas y delega.
- La prueba estatica de seguridad/migracion se actualizo para validar el SQL critico en `postgres_purchases.py`, que ahora es el archivo propietario de aprobacion de compra.

## Medicion despues del corte

- `apps/api/app/modules/credits/postgres_repository.py`: 125 lineas
- `apps/api/app/modules/credits/postgres_purchases.py`: 229 lineas

Antes de los cortes de creditos, `postgres_repository.py` tenia 491 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q -k "stripe or manual or purchase or admin"`: 4 passed, 3 deselected, 1 warning
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

El archivo `postgres_purchases.py` queda en 229 lineas porque concentra una responsabilidad completa: compras de creditos. No lo dividi mas en este corte para evitar partir transacciones delicadas sin necesidad.

## Siguiente corte recomendado

Leer `credits/memory_repository.py`. Ahora que Postgres esta separado, el repositorio in-memory sigue con 298 lineas y puede tener la misma mezcla de compras/referrals/admin adjustments.
