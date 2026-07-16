# BUILDER_REPORT - slice_33A3_fast_fixture_setup_for_delivery_tests

## Estado final

FAST_FIXTURE_SETUP_READY

## Objetivo

Construir tooling seguro para preparar fixtures sintéticos de marketplace delivery en staging sin usar el flujo API pesado uno por uno.

## Archivos creados/modificados

- `scripts/prepare_marketplace_delivery_fixtures.py`
- `scripts/marketplace_delivery_diagnostics.py`
- `apps/api/tests/test_staging_validation_tooling.py`
- `governance/builder_reports/slice_33A3_fast_fixture_setup_for_delivery_tests_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_33A3_fast_fixture_setup_for_delivery_tests_evidence.md`
- `evidence/slice_runs/slice_33A3_fast_fixture_setup_for_delivery_tests_test_results.json`

## Qué construí

- Script de fixture seed directo por DB con guardrails staging:
  - `--env-file`
  - `--run-id`
  - `--businesses`
  - `--ads-per-business`
  - `--output`
  - dry-run por defecto
  - apply solo con `--apply --confirm-staging` y `STAGING_VALIDATION_ACK=<run_id>`
- Inserción sintética batch de:
  - owner users + admin fixture user
  - businesses approved
  - business_access_links active
  - business_payment_methods zelle approved/active
  - credit_wallets
  - active ads
  - credits_ledger hold entries
- Validación de invariantes de fixture:
  - businesses approved
  - ads active y no expirados
  - payment methods approved/active
  - access links active
  - wallet balances no negativos
  - cleanup discoverability por `run_id`
- Invalidación de marketplace cache vía version bump `marketplace:ads`.
- Integración opcional en `marketplace_delivery_diagnostics.py` para usar fixtures preexistentes con `--fixture-run-id`.

## Qué NO construí

- No backend de producto.
- No frontend de producto.
- No migraciones.
- No nuevas reglas de negocio.
- No órdenes, pagos, storage, Telegram real ni Base RPC.
- No c100/c250/c500/c1000 load run.
- No deploy.
- No READY_FOR_REAL_USE.

## Staging fixture validation

Dry-run 250/6:

- Archivo: `evidence/slice_runs/slice_33A3_fixture_dry_run.json`
- Duración: `0.776 ms`
- Planned: `250 businesses`, `1500 ads`

Apply 250/6:

- Archivo: `evidence/slice_runs/slice_33A3_fixture_apply.json`
- run_id: `slice33a3_fixture_apply_20260712114250`
- Duración: `21665.792 ms`
- Inserted:
  - users: `251`
  - businesses: `250`
  - business_access_links: `250`
  - business_payment_methods: `250`
  - credit_wallets: `250`
  - ads: `1500`
  - credits_ledger: `1500`
- Validation:
  - marketplace_visible_ads: `1500`
  - invalid_ads: `0`
  - active_access_links: `250`
  - valid_wallets: `250`
- Cache invalidation: `version_bumped`

There was one first apply attempt (`slice33a3_fixture_apply_20260712114136`) that failed after validation because cleanup discoverability used an incompatible row factory. Dry-run cleanup confirmed that attempt rolled back cleanly with all counts `0`.

## Cleanup

Before:

- Archivo: `evidence/slice_runs/cleanup_slice_33A3_fixture_before.json`
- users: `251`
- businesses: `250`
- business_access_links: `250`
- business_payment_methods: `250`
- credit_wallets: `250`
- ads: `1500`
- credits_ledger: `1500`

Apply:

- Archivo: `evidence/slice_runs/cleanup_slice_33A3_fixture_apply.json`
- Deleted:
  - business_access_links: `250`
  - ads_credit_ledger_refs: `1500`
  - credits_ledger: `1500`
  - ads: `1500`
  - business_payment_methods: `250`
  - credit_wallets: `250`
  - businesses: `250`
  - sessions: `0`
- users_deleted: `0`
- audit_logs_deleted: `0`

After:

- Archivo: `evidence/slice_runs/cleanup_slice_33A3_fixture_after.json`
- businesses: `0`
- business_access_links: `0`
- business_payment_methods: `0`
- credit_wallets: `0`
- ads: `0`
- credits_ledger: `0`
- sessions: `0`
- users: `251` retained by design
- audit logs retained by design

## Validaciones

- `python -m pytest apps/api/tests/test_staging_validation_tooling.py -q --tb=short` -> `70 passed`
- `python -m pytest apps/api/tests -q` -> `275 passed`
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `corepack pnpm --filter @nodo/web build` -> passed
- Artifact scan -> only redacted environment key names in guardrail payloads; no real secret values found.

## Riesgos pendientes

- The next delivery diagnostic should use `--fixture-run-id` or an equivalent preseed step; otherwise c100 can still timeout during inline fixture creation.
- The fast fixture path is test tooling only and must not be treated as product onboarding or business approval logic.

## Confirmaciones

- No producto.
- No frontend.
- No migraciones.
- No deploy.
- No nueva carga c100+.
- No producción.
- No READY_FOR_REAL_USE.
