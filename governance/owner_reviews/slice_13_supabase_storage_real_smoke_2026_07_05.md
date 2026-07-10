# Slice 13 Supabase Storage Real Smoke - Owner Review

Date: 2026-07-05

Status: PASSED_AFTER_OWNER_FIX

Scope:
- Audited `slice_13_supabase_storage_adapter`.
- Found and fixed signed URL base path handling for real Supabase Storage.
- Ran real upload + signed URL + cleanup smoke against the four private staging buckets.
- Did not print secrets, signed URLs or storage paths.
- Did not deploy.
- Did not declare `READY_FOR_REAL_USE`.

Fix Applied:
- File: `apps/api/app/shared/storage/private.py`
- Issue: Supabase real API returns signed URLs beginning with `/object/sign/...`.
- Previous behavior joined that relative URL directly to `SUPABASE_URL`, causing `404`.
- Fixed behavior maps `/object/...` to `{SUPABASE_URL}/storage/v1/object/...`.
- Test updated in `apps/api/tests/test_supabase_storage_adapter.py` to mock the real relative response shape.

Real Smoke Results:
- Bucket `business-verification`: upload OK, signed URL OK, HTTP read OK, cleanup OK.
- Bucket `payment-evidence`: upload OK, signed URL OK, HTTP read OK, cleanup OK.
- Bucket `message-attachments`: upload OK, signed URL OK, HTTP read OK, cleanup OK.
- Bucket `credit-purchase-proofs`: upload OK, signed URL OK, HTTP read OK, cleanup OK.
- Failures: `[]`

Validation:
- `python -m pytest apps/api/tests/test_supabase_storage_adapter.py -q`: 6 passed.
- `python -m ruff check apps/api scripts`: passed.
- `python -m pytest apps/api/tests -q`: 98 passed, 1 known Starlette/httpx warning.
- `python -m compileall apps scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- Frontend scan for service role key, `supabase://`, `storage_path`, signed URL markers and `account_value`: no hits.

Evidence:
- `evidence/slice_runs/supabase_storage_real_smoke_20260705.json`
- `evidence/slice_runs/supabase_storage_real_smoke_after_fix_20260705.json`
- `evidence/slice_runs/slice_13_supabase_storage_adapter_test_results.json`

Result:
- Supabase Storage real staging is ready for continuation.
- Remaining before real use: Railway backend deploy/env, Cloudflare Pages frontend deploy/env, Stripe test mode, Telegram real smoke, CORS/domain hardening and final deploy gate.
