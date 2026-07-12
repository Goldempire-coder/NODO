# slice_28C_order_create_latency_hardening - Evidence

Estado: `READY_FOR_OWNER_REVIEW`

## Builds medidos

- Primera variante: `staging-28c-20260711200635`
- Variante final: `staging-28c2-20260711202300`
- Railway final deployment: `3d204188-2a70-4c67-bb35-7a9466edb065`
- Runner branch: `codex/cloud-scalability-cost-runner`
- Runner commit final: `3ea11fce612113793535319cc9aa31e8f14801e8`

## Archivos principales

- `apps/api/app/modules/orders/create_order_flow.py`
- `apps/api/app/modules/orders/postgres_create_order.py`
- `apps/api/tests/test_order_creation.py`

## Evidencia generada

- `evidence/slice_runs/slice_28C_post_deploy_smoke.json`
- `evidence/slice_runs/slice_28C2_post_deploy_smoke.json`
- `evidence/slice_runs/slice_28C_order_profile_c50_summary.json`
- `evidence/slice_runs/slice_28C2_order_profile_c50_summary.json`
- `evidence/slice_runs/slice_28C2_order_profile_c100_summary.json`
- `evidence/slice_runs/slice_28C_cleanup_verification.json`
- `evidence/slice_runs/slice_28C_github_actions_c50_dispatch.json`
- `evidence/slice_runs/slice_28C2_github_actions_c50_dispatch.json`
- `evidence/slice_runs/slice_28C2_github_actions_c100_dispatch.json`

## Comparacion

| Metric | 28B c50 | 28C2 c50 | Delta |
|---|---:|---:|---:|
| order client p95 | `987.4062ms` | `885.12ms` | `-10.4%` |
| order backend p95 | `571.6427ms` | `456.6227ms` | `-20.1%` |
| errors | `0` | `0` | unchanged |

| Metric | 28B c100 | 28C2 c100 | Delta |
|---|---:|---:|---:|
| order client p95 | `1734.9137ms` | `1661.7075ms` | `-4.2%` |
| order backend p95 | `977.2929ms` | `282.6614ms` | `-71.1%` |
| errors | `0` | `0` | unchanged |

## Resultado funcional

- 28C2 c50: `50x 201`, `150x 200`, errores `0`.
- 28C2 c100: `100x 201`, `300x 200`, errores `0`.
- Perfiles capturados:
  - c50: `order_create=50`, `marketplace_read=150`.
  - c100: `order_create=100`, `marketplace_read=300`.

## Lectura

La primera variante 28C, que combinaba precheck de idempotencia + contexto de orden en una conexion, no mejoro c50. Se reemplazo por 28C2.

28C2 elimina el precheck SQL de idempotencia en el camino fresco de Postgres. La proteccion queda en:

- Redis idempotency lock/record para replay normal.
- Constraint unica `orders_remitter_idempotency_idx`.
- Fallback DB solo si la creacion choca con conflicto.

Esto bajo de forma importante el p95 backend de orden en c100.

## Cleanup

Verificacion posterior:

```json
{
  "gha_29173362553_1_mixed-read-order": {"businesses": 0, "ads_by_business": 0},
  "gha_mixed50_slice28c_fixture_20260711200748": {"businesses": 0, "ads_by_business": 0},
  "gha_29173633187_1_mixed-read-order": {"businesses": 0, "ads_by_business": 0},
  "gha_mixed50_slice28c2_fixture_20260711201814": {"businesses": 0, "ads_by_business": 0},
  "gha_29173933951_1_mixed-read-order": {"businesses": 0, "ads_by_business": 0},
  "gha_mixed100_slice28c2_fixture_20260711202458": {"businesses": 0, "ads_by_business": 0}
}
```

Audit logs y synthetic users quedan retenidos por diseno.

## Validaciones

- `python -m pytest apps\api\tests\test_order_creation.py -q --tb=short`: `15 passed, 1 warning`
- `python -m pytest apps\api\tests -q`: `258 passed, 1 warning`
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Veredicto

`ORDER_CREATE_BACKEND_LATENCY_IMPROVED_WITH_LIMITS`

No `READY_FOR_REAL_USE`.
