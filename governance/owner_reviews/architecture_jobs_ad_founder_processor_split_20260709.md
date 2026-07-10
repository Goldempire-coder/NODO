# Architecture Review - Jobs Ad/Founder Processor Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del procesamiento de anuncios y founder access dentro del worker `expire_and_escalate_orders`.

No se cambiaron reglas de expiracion, notificaciones, auditoria, ordenes, anuncios, founder access, creditos, endpoints, payloads, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/jobs/ad_founder_expiration_processor.py`
- `apps/api/app/modules/jobs/worker.py`

## Cambio realizado

- Se movio el procesamiento de anuncios expirables a `AdFounderExpirationProcessor.process_ads`.
- Se movio el procesamiento de founder access expirado a `AdFounderExpirationProcessor.process_founders`.
- `worker.py` queda como orquestador del job: lock, job run, profiling, delegacion de procesadores, state events y audit helpers.
- Se eliminaron dependencias directas del worker que ya quedaron encapsuladas en procesadores.

## Medicion despues del corte

- `apps/api/app/modules/jobs/worker.py`: 302 lineas
- `apps/api/app/modules/jobs/order_expiration_processor.py`: 318 lineas
- `apps/api/app/modules/jobs/ad_founder_expiration_processor.py`: 75 lineas
- `apps/api/app/modules/jobs/worker_support.py`: 66 lineas

Antes de los cortes de jobs, `worker.py` tenia 648 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_jobs_notifications.py -q`: 7 passed, 1 warning
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

El worker principal ya esta separado en piezas claras. El procesador de ordenes sigue siendo el archivo mas grande del modulo de jobs; si crece mas, el siguiente corte razonable seria dividirlo por familias de estado: waiting payment, payment reported, payment confirmed y delivered.

## Siguiente corte recomendado

Leer primero `apps/api/app/modules/jobs/repository.py` y separar solo si mezcla memory/postgres, row mapping o transacciones largas.
