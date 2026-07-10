# BUILDER_REPORT - slice_08_credits_referrals

Estado final: READY_FOR_OWNER_REVIEW

## Resumen

Se construyo `slice_08_credits_referrals` sobre la base aceptada de slices 00-07. El slice agrega wallet/ledger de creditos, compras Stripe, webhook Stripe firmado e idempotente, pagos manuales Zelle/USDT con comprobante privado, revision admin, ajustes admin, founder audit y referrals con `referral_codes` + `referral_events`.

No se declaro READY_FOR_REAL_USE.

## Archivos Creados

- `apps/api/app/modules/credits/__init__.py`
- `apps/api/app/modules/credits/models.py`
- `apps/api/app/modules/credits/schemas.py`
- `apps/api/app/modules/credits/policy.py`
- `apps/api/app/modules/credits/repository.py`
- `apps/api/app/modules/credits/service.py`
- `apps/api/app/modules/credits/routes.py`
- `apps/api/tests/test_credits_referrals.py`
- `scripts/run_slice_08_tests.py`
- `database/migrations/0009_slice_08_credits_referrals.up.sql`
- `database/migrations/0009_slice_08_credits_referrals.down.sql`
- `evidence/slice_runs/slice_08_credits_referrals_evidence.md`
- `evidence/slice_runs/slice_08_credits_referrals_test_results.json`
- `governance/builder_reports/slice_08_credits_referrals_BUILDER_REPORT.md`

## Archivos Modificados

- `apps/api/app/main.py`
  - Lineas relevantes: 51, 63, 72, 82. Wire de `credit_repository`, CORS `Stripe-Signature`, router `/api/v1`.
- `apps/api/app/core/config.py`
  - Lineas relevantes: 15-16, 42-43, 92-93. Env validation de Stripe backend-only.
- `apps/api/app/core/errors.py`
  - Linea relevante: 59 y bloque de errores de creditos/referrals/Stripe/manual payments.
- `apps/api/app/shared/storage/private.py`
  - Lineas relevantes: 51, 78. Storage privado para `credit_purchase_proof`.
- `apps/api/app/modules/ads/models.py`
  - Linea relevante: 20. Ledger types oficiales sin `refund`/`adjustment`.
- `apps/api/app/modules/ads/service.py`
  - Linea relevante: 194. Audit event `founder_free_use`.
- `apps/web/src/app/page.tsx`
  - Lineas relevantes: 27, 375, 1293, 1522, 1571, 2124. UI credit/referral/admin credit screens.

## Endpoints Construidos

- `GET /api/v1/business/credits/wallet`
- `GET /api/v1/business/credits/ledger`
- `POST /api/v1/business/credits/stripe-checkout`
- `POST /api/v1/business/credits/manual-payment`
- `GET /api/v1/business/referrals`
- `POST /api/v1/business/referrals/apply`
- `POST /api/v1/webhooks/stripe`
- `GET /api/v1/admin/credit-purchases`
- `POST /api/v1/admin/credit-purchases/{purchase_id}/approve`
- `POST /api/v1/admin/credit-purchases/{purchase_id}/reject`
- `POST /api/v1/admin/credits/adjust`

## Migraciones

- `database/migrations/0009_slice_08_credits_referrals.up.sql`
  - Crea `credit_purchases`, `referral_codes`, `referral_events`.
  - Extiende `file_assets` con `resource_type = credit_purchase` y `file_type = credit_purchase_proof`.
  - Alinea `credits_ledger.type` a `purchase`, `founder_free_use`, `referral_bonus`, `hold`, `consume`, `release`, `expire`, `admin_adjustment`.
  - Agrega indices de compras, Stripe session/event/payment intent, idempotencia, referrals y file assets.
- `database/migrations/0009_slice_08_credits_referrals.down.sql`
  - Reversible y restaura checks previos.

## Contratos Cumplidos

- Stripe redirect no acredita creditos.
- Solo webhook Stripe firmado acredita.
- Webhook Stripe duplica seguro sin doble acreditacion.
- Manual Zelle/USDT queda `pending_manual_review`.
- Admin/super_admin aprueba/rechaza manual payment con reason.
- Aprobacion manual acredita wallet y crea ledger `purchase` una sola vez.
- Rechazo manual no acredita.
- `file_assets.resource_type = credit_purchase`.
- `file_assets.file_type = credit_purchase_proof`.
- No se expone private storage path en respuestas/UI.
- `credits_ledger` se trata como append-only desde servicios.
- `refund` y `adjustment` no quedan como tipos activos; se usa `release` y `admin_adjustment`.
- Founder access no salta verificacion ni limites; agrega audit `founder_free_use`.
- Referrals bloquean self-referral, doble uso y doble bonus.
- UI no promete fondos garantizados, escrow, reversa ni garantia de entrega.

## Dependencias

No se instalaron dependencias nuevas. No se agrego Stripe SDK; el slice implementa validacion de firma webhook con HMAC estandar y mantiene la integracion real de checkout externo como riesgo/deploy posterior.

## Comandos Ejecutados

- `corepack pnpm --filter @nodo/web build`
- `python scripts\run_slice_00_tests.py`
- `python scripts\run_slice_01_tests.py`
- `python scripts\run_slice_02_tests.py`
- `python scripts\run_slice_03_tests.py`
- `python scripts\run_slice_04_tests.py`
- `python scripts\run_slice_05_tests.py`
- `python scripts\run_slice_06_tests.py`
- `python scripts\run_slice_07_tests.py`
- `python scripts\run_slice_08_tests.py`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
- `python -m ruff check apps\api scripts`
- `python -m compileall apps scripts`
- Frontend secret/private-data scan desde `scripts/run_slice_08_tests.py`

## Resultados

- Frontend build: OK.
- Slice 00 runner: OK, 6 passed.
- Slice 01 runner: OK, 6 passed.
- Slice 02 runner: OK.
- Slice 03 runner: OK.
- Slice 04 runner: OK.
- Slice 05 runner: OK.
- Slice 06 runner: OK.
- Slice 07 runner: OK.
- Slice 08 runner: OK, 7 passed, 1 inherited Starlette/httpx warning.
- Pytest acumulado: OK, 71 passed, 1 inherited Starlette/httpx warning.
- Ruff: OK.
- Compileall: OK.
- Frontend secret/private-data scan: OK, hits `[]`.

## Evidencia Especifica

- Stripe firmado acredita: `test_stripe_redirect_does_not_credit_and_signed_webhook_credits_once`.
- Stripe invalido rechaza: mismo test valida `STRIPE_SIGNATURE_INVALID`.
- Stripe duplicado no doble acredita: mismo test valida un solo ledger `purchase`.
- Redirect frontend no acredita: mismo test valida wallet en 0 tras checkout.
- Manual payment pending: `test_manual_payment_submit_pending_admin_approve_once_and_reject_never_credits`.
- Admin approve acredita una sola vez: mismo test valida una sola entrada ledger `purchase`.
- Admin reject no acredita: mismo test valida wallet en 0.
- Admin reason requerido: mismo test valida error 422 sin reason.
- RBAC/ownership: wallet guest seguro y support no aprueba.
- Founder/free use: `test_founder_access_remains_audited_credit_free_publish_without_bypassing_verification`.
- Referrals anti self-referral/double bonus: `test_referrals_prevent_self_referral_duplicate_and_award_bonus_once_after_purchase`.
- Ledger append-only: tests validan nuevos ledger rows y no mutacion por retry.
- Wallet no queda negativo: `test_admin_adjustment_requires_admin_and_keeps_wallet_non_negative`.
- Errores seguros: `test_safe_errors_and_migration_contracts_do_not_expose_private_fields_or_legacy_types`.

## Tests No Ejecutados

- Migraciones reales contra PostgreSQL/Supabase no ejecutadas por falta de servicio/credenciales reales.
- Redis real no ejecutado por falta de servicio/credenciales reales.
- Storage privado real no ejecutado; runtime normal sigue usando adapter unavailable hasta configurar storage.
- Stripe checkout real contra API Stripe no ejecutado; no se instalo SDK ni se usaron secretos reales.
- Smoke manual Telegram real pendiente.

## Riesgos Residuales

- Los riesgos heredados siguen vigentes: PostgreSQL/Supabase real, Redis real, storage privado real, smoke Telegram real y warning Starlette/httpx.
- Checkout Stripe real necesita integracion de proveedor/SDK o adapter cuando owner lo autorice para deploy/hardening.
- Runtime Postgres debe ejecutarse contra una DB real para validar constraints e indices fisicamente.

## Scope NO Construido

- No slice 09.
- No fondos de remesas.
- No escrow.
- No procesamiento automatico real de Zelle.
- No cambios a consumo de creditos de ads/orders ya construido, salvo auditoria founder.
- No jobs masivos.
- No admin completo fuera de creditos.
- No READY_FOR_REAL_USE.

## Estado Final

READY_FOR_OWNER_REVIEW
