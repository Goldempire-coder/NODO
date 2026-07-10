# Architecture Review - Jobs Row Mappers Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de mappers y serializacion JSONB del repositorio de jobs.

No se cambiaron SQL, reglas de negocio, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/jobs/row_mappers.py`
- `apps/api/app/modules/jobs/repository.py`

## Cambio realizado

- Se creo `row_mappers.py` para centralizar:
  - `jsonb_metadata`
  - `job_run_from_row`
  - `notification_from_row`
- `repository.py` conserva solo persistencia en memoria y Postgres.
- Se mantuvieron los mismos modelos `JobRunRecord` y `NotificationJobRecord`.
- Se preservo el masking de metadata antes de escribir JSONB.

## Medicion despues del corte

- `apps/api/app/modules/jobs/repository.py`: 166 lineas
- `apps/api/app/modules/jobs/row_mappers.py`: 59 lineas

Antes del corte, `repository.py` tenia 220 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_jobs_notifications.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\jobs apps\api\tests\test_jobs_notifications.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`repository.py` todavia mezcla `InMemoryJobRepository` y `PostgresJobRepository`. El siguiente corte razonable es separar:

- `jobs/memory_repository.py`
- `jobs/postgres_repository.py`
- `jobs/repository.py` como fachada de compatibilidad para imports existentes

Ese corte debe hacerse sin cambiar `app.main`, o manteniendo re-export desde `repository.py`.
