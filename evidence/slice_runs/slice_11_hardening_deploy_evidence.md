# slice_11_hardening_deploy Evidence

Estado final: READY_FOR_OWNER_REVIEW

Fase autorizada: LOCAL_HARDENING_AND_STRESS_ONLY

Fecha: 2026-07-04

## Alcance ejecutado

- Infra local con Docker Compose: PostgreSQL local y Redis local.
- Env template local seguro sin secretos reales.
- Runtime local API usando Postgres/Redis y storage privado local solo por opt-in `PRIVATE_STORAGE_MODE=local_file`.
- Migraciones locales `0001` a `0011` desde cero.
- Validacion de schema real contra Postgres local y Redis local.
- Rollback drill local sobre DB desechable con datos sinteticos.
- Seed sintetico local.
- Smoke E2E local.
- Stress local progresivo capado.
- Frontend build, pytest acumulado, runners 00-11, ruff, compileall y escaneo frontend.

## Infra local

- `docker-compose.local.yml`
  - PostgreSQL: `postgres:16-alpine`, `127.0.0.1:55432`.
  - Redis: `redis:7-alpine`, `127.0.0.1:56379`.
- `docker compose -f docker-compose.local.yml ps`
  - `nodo_postgres_local`: Up, healthy.
  - `nodo_redis_local`: Up, healthy.

## Migraciones y schema

- Comando: `python scripts\apply_local_migrations.py --env-file .env.local.example --reset`
- Resultado: OK.
- Migraciones aplicadas:
  - `0001_slice_00_foundation.up.sql`
  - `0002_slice_01_auth_telegram.up.sql`
  - `0003_slice_02_business_verification.up.sql`
  - `0004_slice_03_ads_marketplace.up.sql`
  - `0005_slice_04_order_creation.up.sql`
  - `0006_slice_05_payment_instructions_reports.up.sql`
  - `0007_slice_06_business_order_ops.up.sql`
  - `0008_slice_07_chat_disputes.up.sql`
  - `0009_slice_08_credits_referrals.up.sql`
  - `0010_slice_09_admin_console.up.sql`
  - `0011_slice_10_jobs_notifications.up.sql`
- Evidencia JSON: `evidence/slice_runs/slice_11_local_migrations.json`

- Comando: `python scripts\validate_local_schema.py --env-file .env.local.example`
- Resultado: OK.
- Tablas detectadas: 23.
- Indices detectados: 128.
- Redis ping: true.
- Failures: `[]`.
- Evidencia JSON: `evidence/slice_runs/slice_11_local_schema_validation.json`

## Rollback drill

- Comando: `python scripts\rollback_local_migrations.py --env-file .env.local.example`
- Resultado final: OK.
- Rollback aplicado en orden descendente `0011` a `0001`.
- Failures finales: `[]`.
- Evidencia JSON: `evidence/slice_runs/slice_11_local_rollback.json`

Hallazgos corregidos durante drill:

- `0009_slice_08_credits_referrals.down.sql` fallaba por filas `credits_ledger` de slice 08 antes de restaurar constraint antigua.
- `0010_slice_09_admin_console.down.sql` fallaba por eventos/valores de resolucion admin antes de restaurar constraint antigua.
- `0006_slice_05_payment_instructions_reports.down.sql` fallaba por `file_assets` de evidencia de pago antes de restaurar constraint antigua.

Fix aplicado:

- Limpieza local de datos introducidos por cada slice antes de restaurar constraints previas en los `down.sql`.
- No se cambiaron reglas runtime ni contratos de negocio.

## Seed local

- Comando: `python scripts\seed_local_synthetic_data.py --env-file .env.local.example --businesses 2 --orders 4`
- Resultado: OK.
- Dataset objetivo:
  - negocios: 2
  - ordenes solicitadas: 4
- Dataset efectivo:
  - negocios: 2
  - ads: 2
  - orders: 2
  - workflow_orders: 2
- Requests: 35.
- Error rate: 0.0.
- Throughput: 4.356 req/s.
- p50: 224.4887 ms.
- p95: 321.3889 ms.
- p99: 400.2582 ms.
- Invariantes:
  - idempotency_duplicates: 0
  - idempotency_replay_conflicts: 0
  - double_credit_consumption: 0
  - double_credit_accreditation: 0
  - negative_balances: 0
  - invalid_transitions: 0
  - redis_failures: 0
  - db_errors: 0
  - timeouts: 0
  - deadlocks: 0
  - job_lock_failures: 0
- Evidencia JSON: `evidence/slice_runs/slice_11_local_seed.json`

## Smoke E2E local

- Comando: `python scripts\local_smoke.py --env-file .env.local.example --run-id rollback-drill-smoke-3`
- Resultado: OK.
- Dataset:
  - businesses: 1
  - remitters: 1
  - admins: 1
  - orders: 1
  - disputes: 1
- Flujo cubierto:
  - `GET /health`
  - `GET /ready`
  - `GET /version`
  - auth Telegram sintetico
  - negocio aprobado
  - documentos privados
  - anuncio
  - marketplace search
  - orden
  - payment instructions
  - payment evidence
  - payment report
  - business confirm-payment
  - mark-delivered
  - chat message
  - dispute open
  - admin dispute resolve
  - job dry-run
  - admin dashboard/metrics
- Requests: 28.
- Error rate: 0.0.
- Throughput: 7.365 req/s.
- p50: 122.8636 ms.
- p95: 286.8681 ms.
- p99: 291.8106 ms.
- Evidencia JSON: `evidence/slice_runs/slice_11_local_smoke.json`

## Stress local

- Comando: `python scripts\stress_local.py --env-file .env.local.example --profile 10 --cap-businesses 5 --cap-orders 10 --run-id stress10cap3`
- Resultado: OK.
- Profile: `10`.
- Limite local aplicado:
  - cap businesses: 5
  - cap orders: 10
- Target efectivo:
  - businesses: 5
  - orders: 10
  - marketplace_searches: 10
  - stripe_events: 5
  - manual_reviews: 5
- Actual:
  - businesses: 5
  - ads: 10
  - orders: 10
  - workflow_orders: 5
- Requests: 98.
- Error rate: 0.0.
- Throughput: 5.1335 req/s.
- p50: 154.1572 ms.
- p95: 307.3146 ms.
- p99: 368.5465 ms.
- Invariantes:
  - idempotency_duplicates: 0
  - idempotency_replay_conflicts: 0
  - double_credit_consumption: 0
  - double_credit_accreditation: 0
  - negative_balances: 0
  - invalid_transitions: 0
  - redis_failures: 0
  - db_errors: 0
  - timeouts: 0
  - deadlocks: 0
  - job_lock_failures: 0
- Evidencia JSON: `evidence/slice_runs/slice_11_local_stress.json`

## QA acumulada

- Runners slice 00-11: OK.
- `corepack pnpm --filter @nodo/web build`: OK.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: `92 passed, 1 warning`.
- `python -m ruff check apps\api scripts`: OK.
- `python -m compileall apps/api scripts`: OK.
- Frontend secret/private scan: OK, hits `[]`.
- Evidencia JSON principal: `evidence/slice_runs/slice_11_hardening_deploy_test_results.json`

## No ejecutado por alcance o limite local

- No Supabase real.
- No Redis cloud.
- No storage real.
- No Stripe live/real.
- No Telegram real.
- No deploy.
- No dataset completo contractual 100%.
- No stress completo de 200 negocios, 10000 usuarios y 2000 ordenes; se dejo harness progresivo y se ejecuto profile 10 con cap local 5/10.

## Riesgos residuales

- Falta validacion con servicios reales cuando owner autorice deploy/hardening externo.
- Falta corrida stress 25/50/100 y dataset completo en maquina o entorno preparado.
- Warning Starlette/httpx sigue presente y aceptado temporalmente.
- `LocalFilePrivateStorage` es solo adaptador local de hardening; runtime normal sin `PRIVATE_STORAGE_MODE=local_file` sigue respondiendo storage unavailable.

## Confirmaciones

- No se declaro READY_FOR_REAL_USE.
- No se usaron credenciales reales.
- No se hizo deploy.
- No se cambiaron reglas de negocio.
- No se inventaron estados/enums.
- No se construyeron features fuera de hardening/stress local.
