# Architecture Review - Ads Hold Transaction Helpers

Status: PASSED_AFTER_REFACTOR

## Scope

Refactor quirurgico de `PostgresAdRepository.release_hold` y `PostgresAdRepository.consume_hold_for_order`.

No se cambiaron reglas de anuncios, creditos, holds, ledger, endpoints, payloads, estados, frontend, contratos, migraciones ni servicios reales.

## Archivo modificado

- `apps/api/app/modules/ads/postgres_repository.py`

## Cambio realizado

Se extrajeron helpers privados para:

- detectar release existente
- bloquear wallet para release
- insertar ledger release
- detectar consume existente
- bloquear wallet para consume
- insertar ledger consume

Cada operacion sigue usando una sola transaccion y las mismas queries principales.

## Medicion despues del corte

- `release_hold`: 29 lineas
- `consume_hold_for_order`: 38 lineas
- `_insert_release_ledger`: 41 lineas
- `_insert_consume_ledger`: 43 lineas
- `apps/api/app/modules/ads/postgres_repository.py`: 461 lineas

Antes del corte:

- `release_hold`: 46 lineas
- `consume_hold_for_order`: 60 lineas

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py apps\api\tests\test_chat_disputes.py -q`: 44 passed, 1 warning
- `python -m ruff check apps\api\app\modules\ads apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py apps\api\tests\test_chat_disputes.py`: PASS
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`_insert_release_ledger` y `_insert_consume_ledger` siguen largos porque contienen SQL completo del ledger. Es aceptable por ahora para no partir una operacion financiera en demasiados fragmentos.

Siguiente corte recomendado:

1. medir `apps/api/app/modules/jobs/worker.py`
2. separar handlers internos del job `expire_and_escalate_orders` si el worker sigue concentrando demasiadas responsabilidades
3. mantener intactas las reglas de expiracion/escalamiento
