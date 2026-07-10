# Architecture Review - Jobs Worker Support Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de soporte puro del worker `expire_and_escalate_orders`.

No se cambiaron reglas de expiracion, escalamiento, notificaciones, disputas, ordenes, anuncios, creditos, endpoints, payloads, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/jobs/worker_support.py`
- `apps/api/app/modules/jobs/worker.py`

## Cambio realizado

Se movio a `worker_support.py`:

- `JobCounters`
- `profile_enabled`
- `profile_mark`
- `serialize_run`
- `counter_payload`
- `attach_profile`

`worker.py` conserva la logica de job y las reglas de estado.

## Medicion despues del corte

- `apps/api/app/modules/jobs/worker.py`: 620 lineas
- `apps/api/app/modules/jobs/worker_support.py`: 66 lineas

Antes del corte, `worker.py` tenia 648 lineas.

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_jobs_notifications.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\jobs apps\api\tests\test_jobs_notifications.py`: PASS
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`worker.py` todavia concentra procesamiento de ordenes, anuncios, founders, notificaciones, disputas y audit.

Siguiente corte recomendado:

1. extraer el procesamiento de ordenes a `jobs/order_expiration_processor.py`
2. mantener `ExpireAndEscalateOrdersWorker` como orquestador
3. no cambiar reglas de `waiting_payment`, `payment_reported`, `payment_confirmed` ni `delivered`
