# Architecture Review - Ads Credit Ledger Mapper Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del mapper de `CreditLedgerRecord` en el modulo de anuncios.

No se cambiaron reglas de anuncios, creditos, holds, ledger, endpoints, payloads, estados, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/ads/row_mappers.py`
- `apps/api/app/modules/ads/postgres_repository.py`

## Cambio realizado

- Se agrego `credit_ledger_from_row` a `ads/row_mappers.py`.
- `PostgresAdRepository.release_hold` ya no arma `CreditLedgerRecord` manualmente.
- `PostgresAdRepository.consume_hold_for_order` ya no arma `CreditLedgerRecord` manualmente.
- Las transacciones y queries quedaron intactas.

## Medicion despues del corte

- `PostgresAdRepository.release_hold`: 45 lineas
- `PostgresAdRepository.consume_hold_for_order`: 59 lineas

Antes del corte:

- `release_hold`: 63 lineas
- `consume_hold_for_order`: 78 lineas

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py -q`: 37 passed, 1 warning
- `python -m ruff check apps\api\app\modules\ads apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py`: PASS
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`release_hold` y `consume_hold_for_order` aun contienen SQL transaccional denso. No se dividio mas en este corte para no mezclar refactor de mappers con cambios en flujo transaccional.

Siguiente corte recomendado:

1. extraer helpers privados de validacion/bloqueo de wallet en `release_hold`
2. extraer helpers privados de update wallet + insert ledger en `consume_hold_for_order`
3. mantener cada operacion en una sola transaccion
