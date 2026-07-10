# slice_13_supabase_storage_adapter Evidence

Status: `READY_FOR_OWNER_REVIEW`

Generated at: `2026-07-05T19:12:09.6446455-04:00`

## Scope Built

- Added Supabase Storage as a private backend adapter behind the existing `private_storage` interface.
- Kept existing upload/reveal endpoints unchanged.
- Kept public API payloads unchanged.
- Kept `storage_path` internal only.
- Added staging env placeholders for the four owner-created private buckets:
  - `business-verification`
  - `payment-evidence`
  - `credit-purchase-proofs`
  - `message-attachments`

## Files Changed

- `.env.staging.example`
- `apps/api/app/core/config.py`
- `apps/api/app/main.py`
- `apps/api/app/shared/storage/private.py`
- `apps/api/tests/test_supabase_storage_adapter.py`

## Validation Results

| Command | Result |
| --- | --- |
| `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_supabase_storage_adapter.py -q` | `6 passed in 1.47s` |
| `python -m ruff check apps\api scripts` | `All checks passed!` |
| `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` | `98 passed, 1 warning in 23.26s` |
| `python -m compileall apps scripts` | exit code `0` |
| `corepack pnpm --filter @nodo/web build` | exit code `0` |

Known warning:

- `StarletteDeprecationWarning` from `fastapi.testclient`/`httpx`, already accepted in previous owner review context.

## Security Scan

Frontend source/build scan:

```powershell
rg -n "SUPABASE_SERVICE_ROLE_KEY|service-role|supabase://|storage_path|signedURL|signedUrl|account_value" apps/web/src apps/web/.next
```

Result: no matches.

Additional frontend scan:

```powershell
rg -n "service-role|sk_live_|whsec_live|BEGIN PRIVATE KEY|storage_path|account_value" apps/web/src apps/web/.next
```

Result: no matches.

Backend/config scan only found expected env variable names, adapter code, and test dummy values. No real secret values were added.

## Supabase Real Smoke

Not executed.

Reason: `.local/supabase_storage_LOCAL_ONLY.txt` was not present. The slice contract makes real Supabase smoke optional and non-blocking unless that local-only credential file exists.

## Residual Risks

- Real Supabase upload + signed URL smoke remains pending until local-only credentials are provided.
- Provider-side bucket policies and service-role permissions still need staging smoke verification.
- Product is not `READY_FOR_REAL_USE`.
