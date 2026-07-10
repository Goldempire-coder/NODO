# Architecture Review - Orders Confirm Payment Transaction Split

Status: PASSED_AFTER_REFACTOR

## Scope

Refactor quirurgico de `PostgresOrderRepository.confirm_business_payment_with_credit_consumption`.

No se cambiaron reglas de negocio, SQL semantico, endpoints, payloads, estados, creditos, jobs, frontend, contratos, migraciones ni servicios reales.

## Archivo modificado

- `apps/api/app/modules/orders/postgres_repository.py`

## Cambio realizado

La funcion transaccional grande fue separada en helpers privados dentro de `PostgresOrderRepository`.

La transaccion sigue siendo una sola:

1. bloquea orden
2. bloquea payment report
3. bloquea anuncio
4. valida consumo previo
5. bloquea wallet
6. consume credit hold
7. archiva anuncio
8. acepta payment report
9. confirma orden
10. hace commit

## Medicion despues del corte

- `confirm_business_payment_with_credit_consumption`: 31 lineas
- `_consume_credit_hold`: 50 lineas
- `_lock_confirmable_order`: 15 lineas
- `apps/api/app/modules/orders/postgres_repository.py`: 594 lineas

Antes del corte, `confirm_business_payment_with_credit_consumption` tenia 136 lineas.

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_business_order_ops.py apps\api\tests\test_chat_disputes.py apps\api\tests\test_jobs_notifications.py -q`: 20 passed, 1 warning
- `python -m ruff check apps\api\app\modules\orders apps\api\tests\test_business_order_ops.py apps\api\tests\test_chat_disputes.py apps\api\tests\test_jobs_notifications.py`: PASS
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`_consume_credit_hold` conserva el insert completo de `credits_ledger` en 50 lineas. Es aceptable por ahora porque separarlo mas podria dispersar una operacion financiera critica.

Siguiente corte recomendado:

1. medir `apps/api/app/modules/ads/repository.py`
2. separar repositorios memory/postgres si siguen mezclados
3. extraer row mappers y operaciones de creditos de anuncios sin tocar reglas
