# slice_28B_order_create_staging_profile - Evidence

Estado: `READY_FOR_OWNER_REVIEW`

## Build y entorno

- Backend staging: `staging-28b-20260711192826`
- Railway deployment: `da75b10b-580c-49d5-a939-69645ad7d6e8`
- Runner branch: `codex/cloud-scalability-cost-runner`
- Runner commit usado por GitHub Actions: `1fbd7afe4b0f01cc8753dbf6125864f8fd7ce7f0`
- Target: `https://nodo-api-production.up.railway.app`
- Guardrails: staging env validado por scripts.

## Corridas

| Run | Concurrency | Requests | Status | Order profiles | Marketplace profiles | Order backend p95 | Marketplace backend p95 | Errors |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| `29172604417` | 50 | 200 | `50x 201`, `150x 200` | 50 | 150 | `571.6427ms` | `97.7111ms` | 0 |
| `29172904002` | 100 | 400 | `100x 201`, `300x 200` | 100 | 300 | `977.2929ms` | `172.2158ms` | 0 |

## Archivos de evidencia

- `evidence/slice_runs/slice_28B_github_actions_c50_retry_dispatch.json`
- `evidence/slice_runs/github_actions_29172604417_mixed_c50_slice28b_retry/gha_29172604417_1_mixed-read-order.json`
- `evidence/slice_runs/slice_28B_order_profile_c50_retry_summary.json`
- `evidence/slice_runs/slice_28B_github_actions_c100_retry_dispatch.json`
- `evidence/slice_runs/github_actions_29172904002_mixed_c100_slice28b_retry/gha_29172904002_1_mixed-read-order.json`
- `evidence/slice_runs/slice_28B_order_profile_c100_retry_summary.json`
- `evidence/slice_runs/slice_28B_cleanup_verification.json`

## Hallazgo

El cuello siguiente medido es `POST /api/v1/orders`.

En c100:

- `order_create` client p95: `1734.9137ms`
- `order_create` backend p95: `977.2929ms`
- `service:get_existing_idempotency` p95: `383.4777ms`
- `audit:order_created_and_ad_moved` p95: `362.3048ms`
- `auth:get_user_by_id` p95: `292.5302ms`
- `transaction:create_order_and_move_ad` p95: `182.4423ms`
- `db_reads:order_create_context` p95: `126.7351ms`

Marketplace ya no es el cuello principal de backend en esta prueba:

- c100 marketplace backend p95: `172.2158ms`
- marketplace DB query count: `1`

## Cleanup

Cleanup ejecutado con `--apply --confirm-staging` para los action run IDs y fixture run IDs.

Verificacion posterior:

```json
{
  "gha_29172604417_1_mixed-read-order": {"businesses": 0, "ads_by_business": 0},
  "gha_mixed50_slice28b_retry_fixture_20260711193850": {"businesses": 0, "ads_by_business": 0},
  "gha_29172904002_1_mixed-read-order": {"businesses": 0, "ads_by_business": 0},
  "gha_mixed100_slice28b_retry_fixture_20260711194620": {"businesses": 0, "ads_by_business": 0}
}
```

Audit logs y usuarios sinteticos quedan retenidos por diseno del cleanup.

## No secretos

No se imprimieron valores reales de `DATABASE_URL`, `REDIS_URL`, tokens, `storage_path`, `account_value`, signed URLs, private keys, seed phrases ni mnemonics.

## Decision

`ORDER_CREATE_BACKEND_BOTTLENECK_IDENTIFIED_WITH_LIMITS`

Siguiente slice recomendado: reducir trabajo redundante en `POST /orders`, empezando por idempotency existing lookup, auth user lookup bajo carga, audit write path y lecturas de contexto.
