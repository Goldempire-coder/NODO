# OWNER VERIFICATION - slice_08_credits_referrals

Estado final: OWNER_ACCEPTED_FOR_NEXT_SLICE

No se declara READY_FOR_REAL_USE.

## Artefactos revisados

- `governance/builder_reports/slice_08_credits_referrals_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_08_credits_referrals_evidence.md`
- `evidence/slice_runs/slice_08_credits_referrals_test_results.json`
- `apps/api/app/modules/credits/*`
- `apps/api/tests/test_credits_referrals.py`
- `database/migrations/0009_slice_08_credits_referrals.up.sql`
- `database/migrations/0009_slice_08_credits_referrals.down.sql`
- `apps/web/src/app/page.tsx`

## Resultado de auditoria owner

El slice 08 construye el alcance contratado: wallet/ledger de creditos, compras Stripe, webhook firmado, pagos manuales Zelle/USDT con comprobante privado, revision admin, ajustes admin, founder audit y referrals.

Durante la auditoria se detectaron dos brechas de seguridad/contrato y fueron corregidas antes de aceptar el slice:

1. Las mutaciones de creditos aceptaban `Idempotency-Key` opcional, aunque el contrato lo exige obligatorio.
2. `PostgresCreditRepository.approve_purchase` no validaba el estado real de `credit_purchases` dentro de la transaccion antes de acreditar.

## Correcciones aplicadas

- `apps/api/app/modules/credits/service.py`
  - Agrega `_require_idempotency_key`.
  - Obliga idempotencia en:
    - Stripe checkout
    - manual payment
    - apply referral
    - admin approve
    - admin reject
    - admin adjust

- `apps/api/app/modules/credits/repository.py`
  - Bloquea `credit_purchases` con `select ... for update`.
  - Revalida estado transaccional antes de acreditar.
  - Permite Stripe solo desde `pending_payment` o `paid`.
  - Permite admin manual approve solo desde `pending_manual_review`.
  - Evita acreditacion si ya existe ledger inconsistente.

- `apps/api/tests/test_credits_referrals.py`
  - Agrega cobertura para `IDEMPOTENCY_KEY_REQUIRED`.
  - Agrega validacion de proteccion transaccional Postgres en el repositorio.

## Validacion ejecutada

- `python scripts\run_slice_00_tests.py`: OK, 6 passed.
- `python scripts\run_slice_01_tests.py`: OK, 6 passed.
- `python scripts\run_slice_02_tests.py`: OK.
- `python scripts\run_slice_03_tests.py`: OK.
- `python scripts\run_slice_04_tests.py`: OK.
- `python scripts\run_slice_05_tests.py`: OK.
- `python scripts\run_slice_06_tests.py`: OK.
- `python scripts\run_slice_07_tests.py`: OK.
- `python scripts\run_slice_08_tests.py`: OK.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_credits_referrals.py -q`: 7 passed, 1 warning.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 71 passed, 1 warning.
- `python -m ruff check apps\api scripts`: OK.
- `python -m compileall apps scripts`: OK.
- `corepack pnpm --filter @nodo/web build`: OK.

## Busquedas de seguridad

- Frontend/API credits no exponen Stripe secrets.
- `storage_path` queda en storage/repos internos, no como respuesta UI/API de creditos.
- Rutas activas de creditos usan `/api/v1`.
- No se construyo slice 09.
- No se construyeron fondos de remesas, escrow, procesamiento automatico real de Zelle ni jobs masivos.

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase pendientes.
- Redis real pendiente.
- Storage privado real pendiente.
- Stripe checkout real/SDK no integrado; webhook firmado e idempotente si esta implementado.
- Smoke manual Telegram real pendiente.
- Warning Starlette/httpx heredado sigue aceptado temporalmente.

## Estado

`slice_08_credits_referrals = OWNER_ACCEPTED_FOR_NEXT_SLICE`
