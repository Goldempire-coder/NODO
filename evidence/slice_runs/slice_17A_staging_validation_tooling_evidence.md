# slice_17A_staging_validation_tooling_evidence

## Estado

READY_FOR_OWNER_REVIEW

## Evidencia de construccion

Se agrego tooling staging aislado en `scripts/` y tests unitarios en `apps/api/tests/test_staging_validation_tooling.py`.

Archivos principales:

- `scripts/staging_guardrails.py`
- `scripts/apply_staging_migrations.py`
- `scripts/validate_staging_schema.py`
- `scripts/staging_storage_smoke.py`
- `scripts/staging_telegram_webhook_smoke.py`
- `scripts/staging_cleanup_synthetic_run.py`
- `scripts/capacity_real.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Guardrails implementados

- `APP_ENV=staging` obligatorio.
- `NODO_STAGING_VALIDATION=1` obligatorio.
- Allowlist DB/API soportada por:
  - `NODO_STAGING_DB_HOST_ALLOWLIST`
  - `NODO_STAGING_API_HOST_ALLOWLIST`
- Acciones mutantes requieren `--confirm-staging`.
- Acciones mutantes con `run_id` requieren `STAGING_VALIDATION_ACK=<run_id>`.
- Produccion/prod se rechaza por marcador en host/URL.
- Secrets se redactan en payloads JSON.

## Migraciones staging

`scripts/apply_staging_migrations.py` soporta:

- `--plan` / `--dry-run` default
- `--apply` explicito
- ledger `nodo_schema_migrations`
- checksum SHA-256 por archivo
- advisory lock PostgreSQL
- output JSON
- sin reset/drop/schema wipe

No se ejecuto contra staging real.

## Capacity remote

`scripts/capacity_real.py` ahora enruta por `remote_base_url` tambien:

- order-create
- same-ad race
- duplicate idempotency
- payment confirm
- mixed

El harness conserva invariantes y agrega bloque `cleanup` en el resultado cuando el target es remoto.

## Storage smoke

`scripts/staging_storage_smoke.py` implementa:

- upload sintetico a bucket privado de business intake
- signed URL corta
- download/checksum
- delete cleanup
- output JSON sin `storage_path` ni signed URL persistida

No se ejecuto contra Supabase real.

## Telegram smoke

`scripts/staging_telegram_webhook_smoke.py` implementa:

- reject-only por defecto con secret invalido
- valid test-chat opcional con `--allow-send --test-chat-id`
- token/secret no se imprimen en JSON

No se ejecuto contra Telegram real.

## Validaciones

| Comando | Resultado |
| --- | --- |
| `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short` | `8 passed, 1 warning` |
| `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` | `146 passed, 1 warning` |
| `python -m ruff check apps\api scripts` | `All checks passed!` |
| `python -m compileall apps\api apps\web\src scripts` | OK |
| `corepack pnpm --filter @nodo/web build` | OK |
| Frontend secret/private scan | Sin coincidencias |

## Scan frontend

Patron:

`SUPABASE_SERVICE_ROLE_KEY|BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|storage_path|account_value|escrow|fondos protegidos|pago garantizado|garantía de entrega|garantia de entrega|NODO recibió dinero`

Targets:

- `apps/web/src`
- `apps/web/.next`
- `apps/web/out`

Resultado: sin coincidencias.

## Pendiente para fase staging real

- Ejecutar migraciones staging con env real y confirmacion owner.
- Validar schema real.
- Ejecutar Redis/Storage/Telegram smokes reales.
- Ejecutar capacity real remoto.
- Ejecutar cleanup real por `run_id`.
- No declarar READY_FOR_REAL_USE hasta autorizacion explicita.
