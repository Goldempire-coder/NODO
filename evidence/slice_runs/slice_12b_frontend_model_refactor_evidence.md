# slice_12b_frontend_model_refactor Evidence

Status: READY_FOR_OWNER_REVIEW

## Refactor Summary

`apps/web/src/hooks/useBusinessWorkspaceModel.ts` was reduced from the slice 12 residual 1315-line monolith into a 200-line composer. State and domain handlers were moved into focused hooks under `apps/web/src/hooks/workspace/`.

The flat model consumed by `WorkspaceShell` and the screen modules was preserved. Endpoint strings, payloads, idempotency key patterns, visible notices, Telegram MainButton behavior, and backend authority boundaries were preserved.

## Size Evidence

| File | Lines | Bytes |
| --- | ---: | ---: |
| `apps/web/src/hooks/useBusinessWorkspaceModel.ts` before | 1315 | 46250 |
| `apps/web/src/hooks/useBusinessWorkspaceModel.ts` after | 200 | 8772 |
| `apps/web/src/hooks/workspace/useWorkspaceState.ts` | 247 | 8883 |
| `apps/web/src/hooks/workspace/useAdminConsoleModel.ts` | 265 | 8453 |
| `apps/web/src/hooks/workspace/useCreditsReferralsModel.ts` | 235 | 7522 |
| `apps/web/src/hooks/workspace/useChatDisputesModel.ts` | 137 | 4047 |
| `apps/web/src/hooks/workspace/useBusinessVerificationModel.ts` | 133 | 4123 |
| `apps/web/src/hooks/workspace/useMarketplaceModel.ts` | 132 | 4130 |
| `apps/web/src/hooks/workspace/usePaymentReportModel.ts` | 127 | 4574 |
| `apps/web/src/hooks/workspace/useRemitterOrdersModel.ts` | 124 | 3695 |
| `apps/web/src/hooks/workspace/useBusinessOrderOpsModel.ts` | 85 | 3286 |
| `apps/web/src/hooks/workspace/useTelegramMainButton.ts` | 54 | 1647 |

No new hook exceeds 300 lines.

## Hook Responsibilities

- `useWorkspaceState.ts`: central frontend state and derived readiness flags.
- `useBusinessVerificationModel.ts`: business load, onboarding update, document upload, verification submit, form update.
- `useMarketplaceModel.ts`: ad search/detail, create ad, list/archived ads, ad mutation.
- `useRemitterOrdersModel.ts`: create/list/detail/extend/cancel remitter orders.
- `usePaymentReportModel.ts`: reveal payment instructions, upload payment evidence, submit payment report.
- `useBusinessOrderOpsModel.ts`: business incoming orders, detail, confirm/reject/deliver operations.
- `useChatDisputesModel.ts`: chat open/refresh/send, attachments, dispute open.
- `useCreditsReferralsModel.ts`: wallet, ledger, Stripe checkout start, manual credit proof, referrals, admin credit review, admin adjustments.
- `useAdminConsoleModel.ts`: admin business review, dashboard, metrics, orders, disputes, audit logs.
- `useTelegramMainButton.ts`: MainButton binding, text, action dispatch, cleanup.
- `useBusinessWorkspaceModel.ts`: composer/orchestrator returning the same flat screen model.

## Validation Evidence

- Frontend build: PASS.
- `run_slice_01_tests.py`: PASS, 6 passed.
- `run_slice_08_tests.py`: PASS, 7 passed, 1 known Starlette/httpx warning.
- `run_slice_09_tests.py`: PASS, 7 passed, 1 known Starlette/httpx warning.
- `run_slice_11_tests.py`: PASS, 8 checks.
- Accumulated backend pytest: PASS, `92 passed, 1 warning`.
- Ruff: PASS.
- Compileall: PASS.
- Frontend source/build scan: PASS, 0 hits.

Detailed command results:

- `evidence/slice_runs/slice_12b_frontend_model_refactor_test_results.json`

## Scope Evidence

Confirmed:

- No endpoints were changed.
- No payloads were changed.
- No copy or disclaimers were changed intentionally.
- No visual design or motion was changed intentionally.
- No backend files were modified.
- No real Supabase, Upstash, Stripe, Telegram, or deploy service was touched.
- No dependencies were installed.
- `READY_FOR_REAL_USE` was not declared.

## Residual Risks

- The screen modules still destructure the full flat model. That preserves behavior, but future maintainability can improve by narrowing props per screen.
- Domain API wrappers remain thin; endpoint calls are now grouped by hook domain, not moved into rich client wrappers. This avoided behavior drift.
