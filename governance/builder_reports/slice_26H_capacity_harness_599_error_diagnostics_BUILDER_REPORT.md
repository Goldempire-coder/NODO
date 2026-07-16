# BUILDER_REPORT - slice_26H_capacity_harness_599_error_diagnostics

Estado final: HARNESS_599_DIAGNOSTICS_READY

Fecha: 2026-07-11 12:48:21 -04:00

## Objetivo

Endurecer solo el harness `scripts/capacity_real.py` para que los errores sinteticos `599` de HTTPX queden diagnosticables sin tocar producto, backend API, frontend, DB, infraestructura ni deploy.

## Archivos modificados

- `scripts/capacity_real.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Construido

- Se agrego `request_error_samples`, separado de `latency_samples`, con limite independiente de 100 errores.
- Se agrego `request_error_summary` con conteos por clasificacion, endpoint y grupo.
- Se agrego clasificacion de errores HTTPX:
  - `CONNECT_TIMEOUT`
  - `READ_TIMEOUT`
  - `WRITE_TIMEOUT`
  - `POOL_TIMEOUT`
  - `REMOTE_DISCONNECT_OR_PROTOCOL_ERROR`
  - `PROTOCOL_ERROR`
  - `UNKNOWN_CLIENT_ERROR`
- Se agrego redaccion/truncado de mensajes de excepcion.
- Se asegura que cada request del harness tenga:
  - `X-Request-Id`
  - `X-Correlation-Id`
  - `X-NODO-Operation-Id`
  - `X-NODO-Surface`
- Los errores `599` ya no dependen del limite de `latency_samples`.

## Campos agregados al JSON

- `request_error_samples`
- `request_error_summary`

Ejemplo de sample:

```json
{
  "method": "GET",
  "endpoint": "/api/v1/ads/search",
  "group": "capacity:marketplace:read",
  "request_id": "req_existing",
  "correlation_id": "corr_staging-run-0001",
  "operation_id": "op_staging-run-0001_capacity_marketplace_read",
  "surface": "client_mini_app",
  "status": 599,
  "exception_class": "ReadTimeout",
  "exception_message_redacted": "read timeout Authorization=<redacted> refresh_token=<redacted>",
  "elapsed_ms": 123.45,
  "response_started": false,
  "classification": "READ_TIMEOUT"
}
```

## Que NO se construyo

- No se toco `apps/api/app`.
- No se toco frontend producto.
- No se tocaron migraciones.
- No se cambio pool, workers, Railway, Supabase, Upstash ni Cloudflare.
- No se hizo deploy.
- No se repitio stress real.
- No se declaro `READY_FOR_REAL_USE`.

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - Resultado: `43 passed, 1 warning`
- `python -m pytest apps\api\tests -q`
  - Resultado: `240 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Riesgos residuales

- Todavia no se repitio una corrida staging con el harness nuevo. El siguiente paso debe ser una corrida acotada para capturar un `599` real con exception class y clasificacion.
- Los matches del scan en `scripts/capacity_real.py` son esperados cuando apuntan a listas de redaccion, nombres de variables prohibidas o helpers de token sintetico. No se detectaron valores reales en los artefactos 26H.

## Confirmacion

- No product code changed.
- No deploy.
- No infrastructure changed.
- No stress rerun.
- No READY_FOR_REAL_USE.
