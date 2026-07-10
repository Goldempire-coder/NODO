# slice_15_scalability_runtime_hardening BUILDER_REPORT

## Estado final

READY_FOR_OWNER_REVIEW

No se declara READY_FOR_REAL_USE.

## Resumen de implementacion

Se construyo solo el scope aprobado de runtime hardening para lecturas de marketplace:

- Auth liviana para `GET /api/v1/ads/search` y `GET /api/v1/ads/{id}`.
- Fallback a auth fuerte cuando el JWT supera `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS`.
- Cache marketplace local + Redis con invalidacion versionada entre workers.
- Guardrail de pool DB bounded con timeout explicito y snapshot de configuracion al boot.
- Tests de seguridad para confirmar que marketplace read no toca repositorio de usuarios con token fresco, pero respeta bloqueo cuando el token ya no esta dentro del TTL de claims.
- Tests de cache versionada para evitar stale cache entre workers.

## Archivos modificados

- `apps/api/app/auth/dependencies.py`
- `apps/api/app/core/config.py`
- `apps/api/app/modules/ads/routes.py`
- `apps/api/app/shared/cache.py`
- `apps/api/app/shared/db/connection.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_ads_marketplace.py`
- `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`
- `evidence/slice_runs/slice_15_scalability_runtime_hardening_test_results.json`
- `evidence/slice_runs/slice_15_scalability_runtime_hardening_evidence.md`
- `governance/builder_reports/slice_15_scalability_runtime_hardening_BUILDER_REPORT.md`

## Endpoints afectados

- `GET /api/v1/ads/search`: usa `require_marketplace_read_user`.
- `GET /api/v1/ads/{id}`: usa `require_marketplace_read_user`; el payload no expone `account_value` ni `storage_path`.

## Endpoints sensibles no debilitados

No se modifico auth en:

- `POST /api/v1/orders`
- payment instructions/report/evidence
- business/admin/credits/chat/disputes/bots
- mutaciones de ads
- mutaciones de orden
- mutaciones admin

## Stress y resultados

### Marketplace c100

- Run id: `slice15_marketplace_c100_20260710095349`
- Archivo: `evidence/slice_runs/slice_15_marketplace_c100.json`
- Log: `evidence/slice_runs/slice_15_marketplace_c100.log`
- Total requests: 1000
- Total errors: 0
- Error rate: 0.0
- Duration: 117.962 s
- Throughput: 8.4773 req/s
- p50: 186.3046 ms
- p95: 343.767 ms
- p99: 407.2485 ms
- Invariant violations: 0

### Marketplace c200

- Run id: `slice15_marketplace_c200_20260710095557`
- Archivo: `evidence/slice_runs/slice_15_marketplace_c200.json`
- Log: `evidence/slice_runs/slice_15_marketplace_c200.log`
- Total requests: 1000
- Total errors: 0
- Error rate: 0.0
- Duration: 123.313 s
- Throughput: 8.1095 req/s
- p50: 518.2419 ms
- p95: 939.6169 ms
- p99: 987.132 ms
- Invariant violations: 0

### Mixed c100

- Run id: `slice15_mixed_c100_20260710095823`
- Archivo: `evidence/slice_runs/slice_15_mixed_c100.json`
- Log: `evidence/slice_runs/slice_15_mixed_c100.log`
- Total requests: 655
- Total errors: 73
- Error rate: 0.1115
- Expected conflict responses: 73 HTTP 409 responses from race/idempotency checks.
- Duration: 213.366 s
- Throughput: 3.0698 req/s
- p50: 246.6842 ms
- p95: 15938.3774 ms
- p99: 16121.629 ms
- Invariant violations: 0

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_ads_marketplace.py -q --tb=short`
  - Resultado: 17 passed, 1 warning.
- `python -m pytest apps\api\tests -q`
  - Resultado: 137 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Resultado: All checks passed.
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: passed.
- `corepack pnpm --filter @nodo/web build`
  - Resultado: passed.
- Stress marketplace c100
  - Resultado: passed.
- Stress marketplace c200
  - Resultado: passed.
- Stress mixed c100
  - Resultado: passed with expected 409 conflict responses and 0 invariant violations.
- Log scan for `too many clients already`, `ReadTimeout`, `ReadError`, `OperationalError`, `RATE_LIMITED`, `500`
  - Resultado: no matches.
- Frontend source/build scan for secrets, `storage_path`, `account_value`, and prohibited claims
  - Resultado: no matches.

## Riesgos residuales

- Esta prueba es local Docker/Postgres/Redis. No autoriza afirmar capacidad 10,000 ni READY_FOR_REAL_USE.
- El auth liviano permite claims-only solo durante `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS` para endpoints marketplace seguros; fuera de esa ventana vuelve a auth fuerte.
- Mixed flow muestra latencias altas en `POST /api/v1/orders` bajo concurrencia local, pero ese endpoint no fue debilitado ni optimizado en slice 15 y no hubo invariantes rotas.

## Confirmaciones de scope

- No se cambiaron reglas de negocio.
- No se cambiaron lifecycles de orden, anuncio, pago, credito ni disputa.
- No se crearon pantallas nuevas.
- No se hizo deploy.
- No se debilito `POST /api/v1/orders`.
- No se debilitaron endpoints de payment instructions/report/evidence.
- No se debilitaron business/admin/credits/chat/disputes/bots.
- No se declara READY_FOR_REAL_USE.
