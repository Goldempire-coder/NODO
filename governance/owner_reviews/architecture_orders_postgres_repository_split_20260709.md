# Architecture Review - Orders Postgres Repository Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del repositorio Postgres de ordenes.

No se cambiaron reglas de negocio, SQL interno, endpoints, payloads, estados, creditos, jobs, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/orders/postgres_repository.py`
- `apps/api/app/modules/orders/repository.py`

## Cambio realizado

- `PostgresOrderRepository` fue movido a `orders/postgres_repository.py`.
- `orders/repository.py` quedo como facade de compatibilidad.
- Los imports existentes desde `app.modules.orders.repository` siguen funcionando.
- `InMemoryOrderRepository` sigue en `orders/memory_repository.py`.

## Medicion despues del corte

- `apps/api/app/modules/orders/repository.py`: 6 lineas
- `apps/api/app/modules/orders/memory_repository.py`: 229 lineas
- `apps/api/app/modules/orders/postgres_repository.py`: 532 lineas

## Validacion ejecutada

- `python -m ruff check apps\api\app\modules\orders apps\api\tests\test_order_creation.py apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_jobs_notifications.py`: PASS
- `python -m pytest apps\api\tests\test_order_creation.py apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_jobs_notifications.py -q`: 30 passed, 1 warning
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`PostgresOrderRepository.confirm_business_payment_with_credit_consumption` sigue siendo una funcion transaccional grande.

Siguiente corte recomendado:

1. Medir y aislar la funcion sin cambiar SQL.
2. Extraer helpers privados para lectura de orden/reporte/ad/credit hold.
3. Extraer helpers privados para update de creditos/ledger/ad/order.
4. Mantener una sola transaccion y validar contra pruebas de ordenes, creditos y jobs.
