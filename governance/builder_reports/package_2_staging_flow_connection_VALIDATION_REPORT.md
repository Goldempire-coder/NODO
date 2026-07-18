# Package 2 - Staging Flow Connection Validation Report

Status: READY_FOR_OWNER_REVIEW
Date: 2026-07-18
Branch: codex/package-2-staging-flow

## Objective

Prepare the three-app staging flow for owner testing without mixing package 2 into the package 1 commit boundary.

Target flow:

1. Business starts registration from the business Telegram bot.
2. Admin finds the intake request.
3. Admin creates, approves, and notifies the business.
4. Business opens NODO Business Mini App.
5. Business configures payment methods and ads.
6. Client finds ads, creates an order, and both sides can track the order.
7. Telegram/order notification infrastructure is visible in configuration.

## Findings

- The backend already connects business intake, admin approval, business access, ads, client marketplace, orders, order notifications, and Base USDC watcher loops.
- The order notification sender is wired into FastAPI lifespan and enabled by default outside test mode.
- The first real-testing blocker was admin intake visibility: the admin panel opened business intake filtered to `submitted`, so a Telegram registration left as `draft` looked like it never arrived.
- Environment template did not list the operational variables for the Telegram Mini App URL, order notification sender, and Base USDC watcher, which made staging setup easier to miss.

## Changes

- Admin intake now defaults to `all`, so submitted and draft records are visible during real owner testing.
- Admin Intake navigation now opens all records, not only submitted ones.
- Admin Intake UI now has clear buttons: `Todas`, `En revision`, `Borradores`, `Aceptadas`.
- Admin Intake empty state explains to try `Todas` when a record is incomplete.
- Draft intake detail now explains that the business started registration but has not finalized it from Telegram.
- `.env.example` now documents:
  - `TELEGRAM_WEB_APP_URL`
  - `ORDER_NOTIFICATION_SENDER_ENABLED`
  - `ORDER_NOTIFICATION_SENDER_INTERVAL_SECONDS`
  - `ORDER_NOTIFICATION_SENDER_BATCH_SIZE`
  - `ONCHAIN_CREDIT_WATCHER_ENABLED`
  - `ONCHAIN_CREDIT_WATCHER_INTERVAL_SECONDS`
  - `ONCHAIN_CREDIT_WATCHER_BATCH_SIZE`
  - `ONCHAIN_CREDIT_WATCHER_TIMEOUT_SECONDS`

## Validation

- `python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short` -> 9 passed
- `python -m pytest apps/api/tests/test_business_intake_bot.py apps/api/tests/test_business_access_control.py apps/api/tests/test_ads_marketplace.py apps/api/tests/test_order_creation.py apps/api/tests/test_jobs_notifications.py -q --tb=short` -> 101 passed
- `python -m pytest apps/api/tests/test_auth_lifecycle_static.py apps/api/tests/test_package_1_sensitive_action_hardening_static.py -q --tb=short` -> 12 passed
- `python -m pytest apps/api/tests -q` -> 379 passed
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `pnpm --filter @nodo/web build` -> passed with bundled Node runtime on PATH

## Skill Review

- `git-workflow-and-versioning`: package 2 is isolated in `C:\Users\carlo\Documents\Playground\NODO-package2-staging-flow` on branch `codex/package-2-staging-flow`; diff is small and focused.
- `code-review-and-quality`: change is limited to admin intake visibility, environment template documentation, static guardrails, and this report. No business rules, financial rules, Telegram runtime, migrations, or large refactors were mixed in.
- `security-and-hardening`: `pnpm audit --audit-level high` returned `No known vulnerabilities found`; no new dependency was added.
- `secret-guard`: explicit scan of changed files returned `No findings`.
- `shipping-and-launch`: package is not deployed yet. Remaining launch gates are provider variables, bot webhook verification, API/web deploy, and owner smoke over the full Telegram/admin/business/client flow.
- `webapp-testing`: `python -m http.server 3101 --directory apps/web/out` returned HTTP `200` through `Invoke-WebRequest`. Playwright/Chromium smoke was attempted twice and failed with `net::ERR_EMPTY_RESPONSE` against the local helper-served URL. This is recorded as an environment/browser-QA limitation, not a functional PASS. Browser QA must be rerun once local/staging is reachable from the intended browser.

## Secret Scan

Scan command:

```powershell
rg -n "private_key|seed phrase|mnemonic|BEGIN PRIVATE|account_value|storage_path|signed_url|console\.log|dangerouslySetInnerHTML|BOT_TOKEN=.+|BUSINESS_INTAKE_BOT_TOKEN=.+|JWT_SECRET=.+|BASE_RPC_URL=https|NODO_CREDIT_RECEIVING_WALLET_BASE=0x" .env.example apps/web/src apps/api/app apps/api/tests/test_auth_lifecycle_static.py apps/api/tests/test_package_1_sensitive_action_hardening_static.py
```

Result:

- No concrete secret values introduced by this package.
- Matches were expected field names, redaction keys, storage abstractions, tests, or payment-method source fields.

## Remaining Before Staging Test

- Configure provider variables in Railway/hosting without exposing values in the repo.
- Verify Telegram webhook URLs for the client bot and business intake bot.
- Deploy API and web candidate.
- Run owner smoke manually:
  - Telegram business registration from a fresh Telegram account.
  - Admin Intake `Todas`.
  - Admin approve and notify.
  - Business Mini App opens from Telegram.
  - Business creates Zelle/USDT method and ad.
  - Client searches, creates order, reports payment.
  - Business receives in-app poll update and Telegram notification.
  - Base USDC credit purchase watcher credits after configured confirmations.

## Out Of Scope

- No deploy.
- No production.
- No secrets added.
- No wallet private key.
- No financial rule changes.
- No infrastructure changes.
- No database migration.
- No READY_FOR_REAL_USE.
