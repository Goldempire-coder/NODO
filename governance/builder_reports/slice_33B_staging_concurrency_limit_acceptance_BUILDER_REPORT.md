# slice_33B_staging_concurrency_limit_acceptance BUILDER_REPORT

## Estado

`STAGING_CONCURRENCY_POLICY_READY`

## Diagnostico oficial

La evidencia de 33A6/33A7 queda convertida en politica operativa:

- Clasificacion: `CONNECTION_TRANSPORT_LIMIT_IDENTIFIED_LOCALLY`.
- GitHub Actions corroboration: `PENDING / BLOCKED_BY_GITHUB_ACTIONS_TOOLING`.
- Producto marketplace: `NOT PRIMARY BOTTLENECK`.
- DB/cache/frontend: `NOT PRIMARY BOTTLENECK`.

Base de evidencia:

- 33A6 mostro TTFB alto tambien en rutas livianas.
- 33A7 reprodujo localmente el problema en `/api/v1/health`, `/api/v1/ready` y `/api/v1/version`.
- En 33A7, `/api/v1/version` tuvo backend p95 bajo con TTFB p95 alto.
- Curl local mostro `tcp_connect_p95` alrededor de 7s en health/version.

No se afirma limite confirmado de Railway porque falta corroboracion GitHub Actions, URL directa o evidencia vendor.

## Nueva regla staging

| Nivel | Uso |
|---|---|
| c25 | Gate de producto permitido |
| c50 | Maximo recomendado para gate de producto staging |
| c100+ | Solo probe explicito de infraestructura/transporte |

c100+ no debe bloquear producto por si solo cuando backend p95 sigue bajo y domina TTFB/tcp_connect. Si c100+ degrada, abre investigacion infra/edge/transporte/harness.

## Cambios realizados

- `operations/STAGING_CONCURRENCY_POLICY.md`
  - Politica oficial c25/c50/c100+.
  - Diagnostico oficial.
  - Backlog 33C/33D/33E.
- `operations/README.md`
  - Link a la politica nueva.
- `operations/runbooks/API_LATENCY_RUNBOOK.md`
  - Seccion de interpretacion de concurrencia staging.
- `control_plane/10_QA/DEPLOY_READINESS_GATE.md`
  - Gate aclarado: c100+ es probe de transporte, no gate de producto.
- `scripts/cloud_load_runner.py`
  - `--run-purpose product-gate|infra-probe`.
  - Default `product-gate`.
  - Rechazo estructurado si product-gate usa concurrencia mayor a c50.
  - Payload de politica incluido en resultados.
- `.github/workflows/nodo-cloud-load-runner.yml`
  - Default de concurrency cambiado a 50.
  - Input `run_purpose`.
  - Paso de `--run-purpose` al runner.
- `apps/api/tests/test_staging_validation_tooling.py`
  - Tests de politica c50/c100+.

## Evidencia de tooling policy

Archivo:

- `evidence/slice_runs/slice_33B_cloud_runner_policy_guard.json`

Resultado:

- c100 con `--run-purpose product-gate` fue rechazado antes de hacer red.
- Mensaje: staging product gates capped at c50; usar `infra-probe` para c100+.

## Backlog pendiente

No ejecutado en este slice:

- `33C_http2_staging_spike`.
- `33D_railway_route_provider_research`.
- `33E_direct_url_or_alt_origin_probe`.

## Validaciones

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`: 93 passed.
- `python -m pytest apps\api\tests -q`: 298 passed.
- `python -m ruff check apps\api scripts`: passed.
- `python -m compileall apps\api apps\web\src scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- `rg` policy checks:
  - No claim falso de limite Railway confirmado.
  - c100 aparece solo como infra-probe/no gate de producto.
  - La referencia de real use aparece solo como prohibicion existente del deploy gate.

## Confirmaciones

- No backend de producto.
- No frontend de producto.
- No migraciones.
- No cambios de infraestructura.
- No deploy.
- No produccion.
- No se declaro real-use readiness.
