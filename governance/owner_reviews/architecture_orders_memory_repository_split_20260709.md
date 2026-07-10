# Architecture Review - Orders Memory Repository Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del repositorio en memoria de ordenes.

No se cambiaron reglas de negocio, endpoints, payloads, estados, creditos, jobs, UI, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/orders/memory_repository.py`
- `apps/api/app/modules/orders/repository.py`

## Cambio realizado

- `InMemoryOrderRepository` fue movido a `orders/memory_repository.py`.
- `orders/repository.py` conserva `PostgresOrderRepository`.
- `orders/repository.py` reexporta `InMemoryOrderRepository` via `__all__` para mantener compatibilidad con imports existentes, incluyendo `app.main`.

## Medicion despues del corte

- `apps/api/app/modules/orders/repository.py`: 536 lineas
- `apps/api/app/modules/orders/memory_repository.py`: 229 lineas

Antes del corte, `orders/repository.py` tenia 700 lineas.

## Validacion ejecutada

- `python -m ruff check NODO\apps\api\app\modules\orders NODO\apps\api\tests\test_order_creation.py NODO\apps\api\tests\test_payment_instructions_reports.py NODO\apps\api\tests\test_business_order_ops.py NODO\apps\api\tests\test_jobs_notifications.py`: PASS
- `python -m pytest apps\api\tests\test_order_creation.py apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_jobs_notifications.py -q`: 30 passed, 1 warning
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`PostgresOrderRepository` sigue siendo grande y contiene operaciones SQL densas, especialmente `confirm_business_payment_with_credit_consumption`.

Siguiente corte recomendado:

1. Mover `PostgresOrderRepository` a `orders/postgres_repository.py`.
2. Dejar `orders/repository.py` como facade de compatibilidad.
3. Despues, separar helpers transaccionales de `confirm_business_payment_with_credit_consumption` sin cambiar su comportamiento.
