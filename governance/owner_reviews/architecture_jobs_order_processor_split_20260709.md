# Architecture Review - Jobs Order Processor Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del procesamiento de ordenes del worker `expire_and_escalate_orders`.

No se cambiaron reglas de expiracion, escalamiento, notificaciones, disputas, ordenes, anuncios, creditos, endpoints, payloads, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/jobs/order_expiration_processor.py`
- `apps/api/app/modules/jobs/worker.py`

## Cambio realizado

Se movio a `OrderExpirationProcessor`:

- listado/evaluacion de ordenes candidatas
- cancelacion de `waiting_payment` vencida
- warning/deadline de `payment_reported`
- warning/deadline de `payment_confirmed`
- recordatorios y auto-complete de `delivered`
- apertura automatica de disputa

`ExpireAndEscalateOrdersWorker` queda como orquestador y conserva:

- lock
- job_runs
- procesamiento de ads
- procesamiento founder
- notification_jobs
- state events
- audit helper

## Medicion despues del corte

- `apps/api/app/modules/jobs/worker.py`: 345 lineas
- `apps/api/app/modules/jobs/order_expiration_processor.py`: 318 lineas
- `apps/api/app/modules/jobs/worker_support.py`: 66 lineas

Antes de los cortes de jobs, `worker.py` tenia 648 lineas.

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_jobs_notifications.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\jobs apps\api\tests\test_jobs_notifications.py`: PASS
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`OrderExpirationProcessor` concentra reglas importantes de ordenes. Esta bien separado del worker, pero puede dividirse mas adelante por estado si crece:

- waiting payment
- payment reported
- payment confirmed
- delivered

Siguiente corte recomendado:

1. extraer procesamiento de ads/founders del worker a `jobs/ad_founder_expiration_processor.py`
2. mantener notification/audit helpers en el worker
3. validar `test_jobs_notifications.py` antes de tocar cualquier regla
