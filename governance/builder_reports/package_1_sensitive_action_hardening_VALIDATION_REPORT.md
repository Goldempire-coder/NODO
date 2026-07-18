# Package 1 Sensitive Action Hardening - Validation Report

Status: VALIDATED_LOCAL_CLEAN_COMMIT
Branch: staging/three-app-connected
Validated at: 2026-07-18
Environment: local Windows Codex runtime
Validated code target: package `fix: harden three-app sensitive actions`

## Scope

This report validates the package:

`fix: harden three-app sensitive actions`

Validation was executed from a clean detached worktree created from commit
`b1d188d9099b8c95eafeeb7248f11f6c09694fae`, before this report was added as documentation.
The documentation-only follow-up does not change runtime code.

## Validated Areas

- Business Mini App sensitive-action hook separation.
- Client Mini App action/navigation state separation.
- Stable idempotency-key helper.
- Base USDC watcher wiring and configuration shape.
- Admin support/action state changes included in the package.
- Static browser render for client, business and admin entry surfaces.
- Secret scan over files changed by the commit.

## Commands And Results

```powershell
python -m pytest apps/api/tests/test_package_1_sensitive_action_hardening_static.py apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
```

Result: `11 passed`

```powershell
python -m pytest apps/api/tests -q
```

Result: `378 passed, 1 warning`

```powershell
python -m ruff check apps/api scripts
```

Result: `All checks passed`

```powershell
python -m compileall apps/api apps/web/src scripts
```

Result: passed

```powershell
pnpm --filter @nodo/web build
```

Result: passed

Build summary:

- `/`: first load JS `104 kB`
- `/business`: first load JS `140 kB`
- shared JS: `103 kB`

## Local Browser Smoke

Static build served locally from `apps/web/out`.

| Surface | Local elapsed | First contentful paint | Console errors |
| --- | ---: | ---: | ---: |
| client | 819.47 ms | 192 ms | 0 |
| business | 571.09 ms | 44 ms | 0 |
| admin | 594.92 ms | 40 ms | 0 |

Observed local rendered states:

- Client and business correctly stopped at Telegram-safe auth entry when no valid Telegram session exists.
- Admin rendered the admin session entry page.

## Secret Scan

Command:

```powershell
python C:\Users\carlo\.codex\skills\secret-guard\scripts\guard.py --format md --files $(git diff --name-only HEAD^ HEAD)
```

Reviewed findings were placeholders, not live secrets:

- `.env.local.example:23` -> `STRIPE_WEBHOOK_SECRET=whsec_local_hardening_placeholder`
- `.env.local.example:52` -> `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=nodo_local_test_bot`

No wallet private key, seed phrase, Telegram bot token, Coinbase API key, Base RPC secret, or live payment secret was found in the changed package.

## Limits

This evidence does not prove:

- Real Telegram Mini App behavior on phone.
- Staging backend connectivity.
- Real bot notification delivery.
- Real Base USDC credit auto-accreditation.
- Production readiness.

Those require a staging walkthrough with backend, bots, admin, client and business connected.

## Repo Boundary

The main working tree still had unrelated pending changes from other packages during validation.
They were not included in the validated package.

This report applies only to the package `fix: harden three-app sensitive actions`.
