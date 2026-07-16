# slice_24A_backend_observability_foundation_BUILDER_REPORT

## Estado final

OBSERVABILITY BACKEND FOUNDATION READY WITH LIMITS

## Construido

- Middleware backend de observabilidad para generar/normalizar:
  - `request_id`
  - `correlation_id`
  - `operation_id`
  - `surface`
- Headers canonicos en respuestas:
  - `X-Request-Id`
  - `X-Correlation-Id`
  - `X-NODO-Operation-Id`
  - `X-NODO-Surface`
- Logging estructurado por request con:
  - method
  - route template
  - status
  - duration_ms
  - request_id
  - correlation_id
  - operation_id
  - surface
  - error_code cuando aplica
- Redaccion centralizada para logs operativos.
- Errores seguros con `X-Request-Id` y `X-NODO-Error-Code`.
- CORS actualizado para aceptar/exponer headers de correlacion.
- Tests de headers/correlation, redaccion, error 500 seguro, webhook malformado, conflicto/idempotencia simulado y apagado por env.

## No construido

- No session replay frontend persistente.
- No frontend breadcrumbs.
- No tabla `observability_events`.
- No migraciones.
- No UI Admin de observability.
- No proveedor externo SaaS.
- No deploy.
- No `READY_FOR_REAL_USE`.

## Archivos modificados/creados por 24A

- `apps/api/app/shared/logging_redaction.py`
- `apps/api/app/shared/observability.py`
- `apps/api/app/core/logging.py`
- `apps/api/app/core/errors.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_backend_observability_foundation.py`
- `governance/builder_reports/slice_24A_backend_observability_foundation_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_24A_backend_observability_foundation_evidence.md`
- `evidence/slice_runs/slice_24A_backend_observability_foundation_test_results.json`

Nota: el worktree ya tenia cambios previos de otros slices. No se revirtieron ni limpiaron cambios ajenos.

## Ejemplos de log redacted

Request completado:

```txt
backend_request_completed {
  event=backend_request_completed,
  method=GET,
  route_template=/api/v1/health,
  status=200,
  duration_ms=...,
  request_id=req_log,
  correlation_id=corr_log,
  operation_id=op_log,
  surface=client_mini_app,
  error_code=null
}
```

Error no manejado:

```txt
api_unhandled_error {
  request_id=req_boom,
  correlation_id=corr_boom,
  operation_id=op_boom,
  surface=unknown,
  error_code=INTERNAL_ERROR,
  exception_class=RuntimeError
}
```

El log no incluye stack trace crudo ni mensaje de excepcion con posibles secretos.

## Validaciones ejecutadas

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_backend_observability_foundation.py -q --tb=short`
  - Resultado: `11 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `221 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Scans ejecutados

Patrones:

- `storage_path`
- `account_value`
- `Authorization`
- `refresh_token`
- `access_token`
- `Telegram initData`
- `BOT_TOKEN`
- `BUSINESS_INTAKE_BOT_TOKEN`
- `DATABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `private key`
- `seed phrase`
- `signed URL`

Resultado:

- No se encontraron valores secretos reales en build/source.
- Los hits restantes corresponden a:
  - denylist/redaction patterns;
  - CORS `Authorization`;
  - fixtures de tests que verifican redaccion.

## Riesgos residuales

- 24A no implementa frontend breadcrumbs ni session replay; solo deja base backend.
- 24A no crea `observability_events`, retention cleanup ni Admin Web diagnostics.
- Algunos logs especificos de dominio siguen dependiendo de futuras instrumentaciones por modulo si se requiere granularidad mas alla del request log.

## Confirmaciones

- No cambie reglas de negocio.
- No cambie lifecycles de ordenes, creditos, ads, soporte, disputas o bots.
- No cree migraciones.
- No cree session replay persistente.
- No toque frontend de producto.
- No agregue proveedor externo.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.
