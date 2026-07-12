# slice_28D_order_create_cte_experiment - evidence

Estado: REJECTED_AND_ROLLED_BACK

## Qué se probó

Se probó combinar la reserva del anuncio y creación de orden en una sola sentencia SQL. La hipótesis era reducir una vuelta a Postgres dentro de la transacción de `POST /api/v1/orders`.

## Resultado

El experimento no se aceptó.

| Escenario | Requests | Status | Order client p95 | Order backend p95 |
|---|---:|---|---:|---:|
| 28D c50 | 200 | 50x201, 150x200 | 780.5787 ms | 440.2408 ms |
| 28C2 c50 | 200 | 50x201, 150x200 | 885.1200 ms | 456.6227 ms |
| 28D c100 | 400 | 100x201, 300x200 | 1203.2337 ms | 594.5846 ms |
| 28C2 c100 | 400 | 100x201, 300x200 | 1661.7075 ms | 282.6614 ms |

El c50 tuvo mejora pequeña. El c100 tuvo regresión backend fuerte. Se rechaza el cambio porque el backend p95 es la métrica más representativa para esta optimización.

## Acciones de seguridad

- Se revirtió el cambio.
- Se redesplegó staging con build rollback `staging-28d-rollback-20260711210924`.
- Se limpió staging para los run_ids c50/c100.
- Se verificó que no quedaran negocios, anuncios ni órdenes de los fixtures 28D.

## Archivos de evidencia

- `evidence/slice_runs/github_actions_29174473665_mixed_c50_slice28d/gha_29174473665_1_mixed-read-order.json`
- `evidence/slice_runs/github_actions_29174774724_mixed_c100_slice28d/gha_29174774724_1_mixed-read-order.json`
- `evidence/slice_runs/slice_28D_cloud_comparison_summary.json`
- `evidence/slice_runs/slice_28D_cleanup_summary.json`
- `evidence/slice_runs/slice_28D_cleanup_verification.json`
- `evidence/slice_runs/slice_28D_final_version_check.json`

## Confirmación

No queda cambio de código 28D. No se cambió infraestructura, pool, workers, Supabase, Upstash ni Cloudflare. No se declaró `READY_FOR_REAL_USE`.
