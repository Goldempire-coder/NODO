# Architecture Review - Jobs Service Serializers Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de serializacion de respuestas del servicio admin de jobs.

No se cambiaron permisos, rate limits, idempotencia, audit events, ejecucion del worker, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/jobs/serializers.py`
- `apps/api/app/modules/jobs/service.py`

## Cambio realizado

- Se creo `serializers.py` para centralizar:
  - `job_run_summary`
  - `job_run_detail`
- `JobService` conserva la logica de caso de uso admin:
  - validar permisos
  - rate limit
  - listar runs
  - ver detalle
  - ejecutar dry-run con idempotencia
  - auditar acciones
- El masking de metadata sigue aplicado en `job_run_detail`.

## Medicion despues del corte

- `apps/api/app/modules/jobs/service.py`: 123 lineas
- `apps/api/app/modules/jobs/serializers.py`: 31 lineas

Antes del corte, `service.py` tenia 146 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_jobs_notifications.py -q`: 7 passed, 1 warning
- `python -m ruff check apps\api\app\modules\jobs apps\api\tests\test_jobs_notifications.py`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`service.py` aun contiene helpers de profiling internos. No los movi porque estan muy acoplados al dry-run y no justifican otro corte inmediato salvo que el servicio crezca.

## Siguiente corte recomendado

Hacer lectura de `apps/api/app/modules/credits/repository.py`, porque los modulos de creditos suelen concentrar ledger, compras manuales, Stripe, admin adjustments y referrals. Ese tipo de archivo puede volverse mas riesgoso para escala que jobs service.
