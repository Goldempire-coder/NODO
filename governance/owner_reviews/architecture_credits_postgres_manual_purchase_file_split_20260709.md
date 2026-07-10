# Architecture Review - Credits Manual Purchase File Helper Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del insert de `file_assets` para comprobantes de compra manual de creditos.

No se cambiaron reglas de compra manual, storage, estados, admin review, ledger, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/credits/postgres_manual_purchase.py`
- `apps/api/app/modules/credits/postgres_repository.py`

## Cambio realizado

- Se creo `insert_credit_purchase_proof_file_pg`.
- `create_manual_purchase` sigue:
  - creando el `purchase_id`
  - insertando `credit_purchases`
  - asignando `proof_file_id`
  - haciendo commit de la misma transaccion
- El insert de `file_assets` queda aislado en helper transaccional.

## Medicion despues del corte

- `apps/api/app/modules/credits/postgres_repository.py`: 386 lineas
- `apps/api/app/modules/credits/postgres_manual_purchase.py`: 23 lineas

Antes de los cortes de creditos, `postgres_repository.py` tenia 491 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q -k "manual or credit"`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

Este corte fue intencionalmente pequeno. Mejora separacion, pero el archivo principal sigue grande. Los siguientes cortes con mas impacto son:

- separar helpers Postgres de referrals (`get_or_create_referral_code`, `apply_referral_code`, `list_referral_events_for_business`)
- separar helper de admin adjustment (`adjust_wallet`)

## Siguiente corte recomendado

Leer primero los metodos de referral en `credits/postgres_repository.py`. Son un bloque natural y menos riesgoso que tocar `approve_purchase` otra vez.
