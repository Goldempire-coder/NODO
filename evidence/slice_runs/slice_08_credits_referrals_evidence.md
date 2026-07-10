# slice_08_credits_referrals Evidence

Status: READY_FOR_OWNER_REVIEW

## Scope Built

- Business credit wallet and ledger endpoints.
- Stripe checkout purchase creation without frontend redirect crediting.
- Signed Stripe webhook crediting with duplicate protection.
- Manual Zelle/USDT credit purchase submission with private `file_assets` proof.
- Admin/super_admin manual payment approval and rejection with required reason.
- Admin credit adjustment using `admin_adjustment` ledger type.
- Founder free-use audit event integration.
- Referral code and referral event flow using `referral_codes` + `referral_events`.
- Telegram Mini App shell screens for business credits/referrals/admin credit review.

## Contract Evidence

- Canonical API routes added in `apps/api/app/modules/credits/routes.py`.
- Runtime repositories wired in `apps/api/app/main.py`.
- Stripe secrets are backend env-only via `apps/api/app/core/config.py`.
- Safe error codes added in `apps/api/app/core/errors.py`.
- Private credit purchase proof storage added in `apps/api/app/shared/storage/private.py`.
- Canonical active ledger types set in `apps/api/app/modules/ads/models.py`.
- Founder free-use audit emitted in `apps/api/app/modules/ads/service.py`.
- Migration `database/migrations/0009_slice_08_credits_referrals.up.sql` creates:
  - `credit_purchases`
  - `referral_codes`
  - `referral_events`
  - file asset checks for `credit_purchase` and `credit_purchase_proof`
  - official `credits_ledger.type` check without legacy `refund`/`adjustment`

## Test Results

- `corepack pnpm --filter @nodo/web build`: OK.
- `python scripts\run_slice_00_tests.py`: OK, 6 passed.
- `python scripts\run_slice_01_tests.py`: OK, 6 passed.
- `python scripts\run_slice_02_tests.py`: OK.
- `python scripts\run_slice_03_tests.py`: OK.
- `python scripts\run_slice_04_tests.py`: OK.
- `python scripts\run_slice_05_tests.py`: OK.
- `python scripts\run_slice_06_tests.py`: OK.
- `python scripts\run_slice_07_tests.py`: OK.
- `python scripts\run_slice_08_tests.py`: OK, 7 passed, 1 inherited Starlette/httpx warning.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: OK, 71 passed, 1 inherited Starlette/httpx warning.
- `python -m ruff check apps\api scripts`: OK.
- `python -m compileall apps scripts`: OK.
- Frontend secret/private-data scan: OK, no hits for Stripe secrets, private storage path, private account field, or prohibited copy.

## Sensitive Data Evidence

- API public purchase/file responses do not expose private storage path.
- Frontend source/build scan returned no hits in `slice_08_credits_referrals_test_results.json`.
- Stripe secret values are not read by frontend and are not returned in API responses.
- Manual proof files use private storage adapter and `file_assets.resource_type = credit_purchase`.

## Residual Risks

- Real PostgreSQL/Supabase migrations remain unexecuted until credentials/service are available.
- Real Redis remains unverified until service credentials are available.
- Real private storage remains unavailable in non-test runtime by design; normal runtime returns safe storage errors until configured.
- Real Stripe SDK/API checkout creation is not integrated; this slice implements governed backend checkout/session record and signed webhook behavior without adding a dependency.
- Smoke manual Telegram real remains pending.
- Starlette/httpx warning remains accepted from prior owner review.

## Scope Not Built

- No slice 09 work.
- No remittance funds handling.
- No escrow.
- No automatic Zelle processing.
- No changes to order/ad credit consumption semantics outside founder audit integration.
- No jobs.
- No full admin beyond credit review/adjustment scope.
- No READY_FOR_REAL_USE declaration.
