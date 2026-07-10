# Architecture P1.9 - Admin Audit Logs Hook

Status: PASSED_AFTER_FIX

## Objective

Move Admin Web audit log state and loading logic out of `useAdminWebModel.ts` into a focused hook.

## Problem Corrected

`useAdminWebModel.ts` still owned audit log state and called the admin audit API directly.

That kept feature-specific responsibility inside the Admin Web composer.

## Files Changed

- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/hooks/admin-web/useAdminAuditLogsModel.ts`

## Responsibility Moved

Moved into `useAdminAuditLogsModel.ts`:

- `auditLogs`
- `auditFilter`
- `setAuditFilter`
- `loadAuditLogs`
- direct use of `listAdminAuditLogs`

`useAdminWebModel.ts` now composes `useAdminAuditLogsModel` and re-exports the same fields/actions to existing Admin Web screens.

## Evidence

Line counts:

- `apps/web/src/hooks/useAdminWebModel.ts`: 221 lines
- `apps/web/src/hooks/admin-web/useAdminAuditLogsModel.ts`: 44 lines

Remaining state inside `useAdminWebModel.ts`:

```txt
view
busy
notice
reason
pendingAction
```

Targeted scan:

```txt
No direct audit log state/API remains in useAdminWebModel.ts.
Only useAdminAuditLogsModel import/composition remains.
```

## Validation

```txt
corepack pnpm --filter @nodo/web build
PASS

$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
133 passed, 1 warning

python -m ruff check apps\api scripts
PASS

python -m compileall apps\api scripts
PASS
```

Known warning:

```txt
StarletteDeprecationWarning from fastapi.testclient/httpx
```

## Not Changed

- No backend behavior changed.
- No endpoints changed.
- No payloads changed.
- No UI layout changed.
- No copy/disclaimers changed.
- No deploy executed.
- No real-service configuration changed.
- No `READY_FOR_REAL_USE` declared.

## Residual Risk

`useAdminWebModel.ts` is now mostly a composer. Remaining future cleanup should focus on surface-level navigation or extracting shared admin critical-action confirmation only if it becomes reused elsewhere.
