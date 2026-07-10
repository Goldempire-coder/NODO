# Architecture Review - Jobs Repository Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de repositorios de jobs por runtime: memoria y Postgres.

No se cambiaron SQL, reglas de negocio, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/jobs/memory_repository.py`
- `apps/api/app/modules/jobs/postgres_repository.py`
- `apps/api/app/modules/jobs/repository.py`

## Cambio realizado

- Se movio `InMemoryJobRepository` a `memory_repository.py`.
- Se movio `PostgresJobRepository` a `postgres_repository.py`.
- `repository.py` quedo como fachada de compatibilidad para imports existentes.
- `app.main` sigue importando desde `app.modules.jobs.repository`, sin cambio de contrato interno.

## Medicion despues del corte

- `apps/api/app/modules/jobs/repository.py`: 6 lineas
- `apps/api/app/modules/jobs/memory_repository.py`: 52 lineas
- `apps/api/app/modules/jobs/postgres_repository.py`: 119 lineas
- `apps/api/app/modules/jobs/row_mappers.py`: 59 lineas

Antes de los cortes, `repository.py` tenia 220 lineas y mezclaba mappers, memoria y Postgres.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_jobs_notifications.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\jobs apps\api\tests\test_jobs_notifications.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

El modulo jobs ya quedo separado en worker, procesadores, soporte, mappers y repositorios. El archivo mas grande sigue siendo `order_expiration_processor.py`; no lo dividi mas porque ya representa una responsabilidad clara: procesar estados de orden dentro del job.

## Siguiente corte recomendado

Leer primero `apps/api/app/modules/jobs/service.py`. Si mezcla request/response admin, ejecucion del worker, repositories y serializacion, separar una capa de `jobs/serializers.py` o `jobs/admin_service.py` antes de tocar comportamiento.
