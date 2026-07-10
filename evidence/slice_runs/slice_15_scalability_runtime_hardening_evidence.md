# slice_15_scalability_runtime_hardening Evidence

## Estado

READY_FOR_OWNER_REVIEW

No READY_FOR_REAL_USE.

## Implementacion validada

- Auth liviana para lecturas seguras de marketplace en:
  - `GET /api/v1/ads/search`
  - `GET /api/v1/ads/{id}`
- Fallback a auth fuerte cuando el token supera `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS`.
- Cache marketplace versionado con capa local + Redis para invalidacion entre workers.
- Guardrail de pool DB bounded con timeout explicito y snapshot de configuracion al boot.
- No se modificaron mutaciones sensibles ni reglas de negocio.

## Evidencia de stress

### Marketplace c100

- Archivo: `evidence/slice_runs/slice_15_marketplace_c100.json`
- Log: `evidence/slice_runs/slice_15_marketplace_c100.log`
- Run id: `slice15_marketplace_c100_20260710095349`
- Target: 20 businesses, 4 ads/business, 120 remitters, 1000 marketplace reads, concurrency 100.
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

- Archivo: `evidence/slice_runs/slice_15_marketplace_c200.json`
- Log: `evidence/slice_runs/slice_15_marketplace_c200.log`
- Run id: `slice15_marketplace_c200_20260710095557`
- Target: 20 businesses, 4 ads/business, 240 remitters, 1000 marketplace reads, concurrency 200.
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

- Archivo: `evidence/slice_runs/slice_15_mixed_c100.json`
- Log: `evidence/slice_runs/slice_15_mixed_c100.log`
- Run id: `slice15_mixed_c100_20260710095823`
- Target: 5 businesses, 18 ads/business, 100 remitters, 500 marketplace reads, marketplace concurrency 100, 50 order creates, 50 same-ad race requests, 20 payment confirms.
- Total requests: 655
- Total errors: 73
- Error rate: 0.1115
- Expected conflicts: 73 HTTP 409 responses from same-ad and same-order race checks.
- Duration: 213.366 s
- Throughput: 3.0698 req/s
- p50: 246.6842 ms
- p95: 15938.3774 ms
- p99: 16121.629 ms
- Invariant violations: 0

## Log scan

Searched logs:

- `evidence/slice_runs/slice_15_marketplace_c100.log`
- `evidence/slice_runs/slice_15_marketplace_c200.log`
- `evidence/slice_runs/slice_15_mixed_c100.log`

Terms checked:

- `too many clients already`
- `ReadTimeout`
- `ReadError`
- `OperationalError`
- `RATE_LIMITED`
- `"500"`
- `"status_code": 500`
- `status_code.*500`

Result: no matches.

## Validation

- `python -m pytest apps\api\tests\test_ads_marketplace.py -q --tb=short`: 17 passed, 1 warning.
- `python -m pytest apps\api\tests -q`: 137 passed, 1 warning.
- `python -m ruff check apps\api scripts`: passed.
- `python -m compileall apps\api apps\web\src scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- Frontend source/build scan for secrets, `storage_path`, `account_value`, and prohibited claims: no matches.

## Riesgos residuales

- Esta evidencia es local Docker/Postgres/Redis; no declara capacidad 10,000 ni READY_FOR_REAL_USE.
- `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS` limita stale-auth risk en marketplace reads; tokens mas viejos vuelven a auth fuerte.
- Mixed flow conserva respuestas 409 esperadas en condiciones de carrera; no son fallos de infraestructura ni invariantes rotas.
