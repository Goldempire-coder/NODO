# SYNTHETIC STAGING CLEANUP - 2026-07-08

## Estado

PASSED_FOR_PRODUCT_DATA_CLEANUP

No se declara READY_FOR_REAL_USE.

## Alcance

Se creo y ejecuto una herramienta segura para limpiar datos sinteticos de stress por `run_id` contra staging real.

Script:

- `scripts/cleanup_synthetic_run.py`

Modo seguro:

- Por defecto corre en `dry_run`.
- Solo borra con `--execute`.
- Valida formato de `run_id`.
- Genera evidencia JSON.

## Decision De Seguridad

El cleanup borra datos de producto sinteticos:

- sesiones
- negocios
- verification submissions
- access links
- payment methods
- wallets
- ads
- credits ledger
- ordenes
- state events
- payment reports
- mensajes/adjuntos si existen
- disputas/eventos si existen
- credit purchases/referrals si existen
- notification jobs si existen
- business intake requests si existen
- file assets

No borra:

- `users`
- `audit_logs`

Motivo:

- `audit_logs` es append-only y tiene triggers anti-update/delete.
- `audit_logs.actor_user_id` referencia `users`.
- Borrar usuarios requeriria una purga especial que romperia la garantia de auditoria historica. No se hizo.

## Validacion Del Script

- `python -m ruff check scripts/cleanup_synthetic_run.py`: OK.
- `python -m compileall scripts/cleanup_synthetic_run.py`: OK.

## Run Limpiado Primero

Run:

- `real_services_stress_profile10_cap10_20260708_150640`

Dry-run inicial:

- businesses: 4
- ads: 10
- orders: 10
- payment_reports: 4
- credits_ledger: 18
- file_assets: 20
- sessions: 6
- audit_logs_retained: 129

Primer execute:

- fallo por FK segura: `credits_ledger_related_order_fk`.
- No hubo commit.
- Se corrigio el orden de borrado.

Execute final:

- businesses: 4
- ads: 10
- orders: 10
- payment_reports: 4
- credits_ledger: 18
- file_assets: 20
- sessions: 6

Postcheck:

- product matches: 0
- sessions: 0
- users retained: 6
- audit retained: 129

Evidencia:

- `evidence/slice_runs/cleanup_dry_run_real_services_stress_profile10_cap10_20260708_150640.json`
- `evidence/slice_runs/cleanup_dry_run2_real_services_stress_profile10_cap10_20260708_150640.json`
- `evidence/slice_runs/cleanup_execute2_real_services_stress_profile10_cap10_20260708_150640.json`
- `evidence/slice_runs/cleanup_postcheck_real_services_stress_profile10_cap10_20260708_150640.json`

## Runs Recientes Limpiados

| run_id | businesses | ads | orders | ledger | files | sessions |
|---|---:|---:|---:|---:|---:|---:|
| `real_services_stress_profile10_cap5_20260708_150150` | 3 | 5 | 5 | 11 | 15 | 5 |
| `real_services_stress_profile10_cap_20260708_144844` | 5 | 25 | 15 | 35 | 25 | 7 |
| `real_services_concurrency_medium_20260708_144416` | 1 | 20 | 20 | 21 | 4 | 23 |
| `real_services_stress_initial_after_job_fix_20260708_142345` | 2 | 2 | 2 | 6 | 10 | 4 |
| `real_services_stress_initial_20260708_133709` | 2 | 2 | 2 | 6 | 10 | 4 |
| `real_services_concurrency_small_20260708_133407` | 1 | 10 | 10 | 11 | 4 | 11 |

## Postcheck Final

Todos los runs revisados quedaron con:

- product matches: 0
- sessions: 0

Usuarios y auditoria retenidos:

| run_id | users retained | audit retained |
|---|---:|---:|
| `real_services_stress_profile10_cap5_20260708_150150` | 5 | 86 |
| `real_services_stress_profile10_cap_20260708_144844` | 7 | 199 |
| `real_services_concurrency_medium_20260708_144416` | 23 | 156 |
| `real_services_stress_initial_after_job_fix_20260708_142345` | 4 | 53 |
| `real_services_stress_initial_20260708_133709` | 4 | 53 |
| `real_services_concurrency_small_20260708_133407` | 11 | 82 |
| `real_services_stress_profile10_cap10_20260708_150640` | 6 | 129 |

## Resultado

Staging quedo limpio de datos de producto sinteticos recientes del 2026-07-08.

Siguiente paso recomendado:

1. Reintentar `profile 10 cap-orders 25` con checkpoint.
2. Si pasa, limpiar el nuevo `run_id`.
3. Luego pasar a `cap-orders 50`.
