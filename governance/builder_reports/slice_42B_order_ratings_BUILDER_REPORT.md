# Slice 42B - Order Ratings Builder Report

Date: 2026-07-21

## Status

`READY_FOR_OWNER_REVIEW`

This slice adds a client-only, post-order rating flow. A client may submit one
integer rating from 1 through 5 for an owned `completed` order. The backend
validates eligibility, stores the rating, and recalculates the business public
reputation in the same database transaction.

## Scope Delivered

- `POST /api/v1/orders/{order_id}/rating` with mandatory idempotency.
- Backend-authoritative order-detail `rating` state with `can_rate`,
  `already_rated`, and `stars`.
- Ownership, completed-state, closed-dispute, self-rating, duplicate, payload,
  and actor-role controls.
- Transactional PostgreSQL rating insertion and public reputation aggregate
  recalculation.
- Equivalent locked in-memory behavior for tests.
- Minimal client Mini App star selector with an action-specific busy state.
- Safe `client_order_rating_submit` breadcrumb without stars or payload data.
- AFOS-aligned API, security, QA, screen, error, and action-matrix contracts.

## Data And Migration Decision

No migration was added. Migration
`0033_business_reputation_foundation` already provides the required `ratings`
table, uniqueness constraint, rating bounds, and business
reputation aggregate columns.

## Security And Privacy

- Foreign orders use the existing non-disclosing not-found behavior.
- Business and admin actors cannot create ratings.
- Only strict integer values 1 through 5 are accepted; comments and extra
  fields are rejected.
- An `admin_resolved` order is rateable only after it is `completed` and its
  dispute is closed.
- Duplicate requests cannot create a second rating.
- Public responses do not expose `risk_level`, `trust_level`, antifraud
  signals, or internal reputation data.
- Audit and frontend telemetry omit rating payloads and sensitive data.

## Validation

- `python -m pytest apps/api/tests/test_order_ratings.py -q --tb=short`
  - 21 passed; one pre-existing Starlette TestClient deprecation warning.
- `python -m pytest apps/api/tests/test_business_reputation_foundation.py apps/api/tests/test_ads_marketplace.py -q --tb=short`
  - 51 passed; one pre-existing Starlette TestClient deprecation warning.
- `python -m pytest apps/api/tests -q`
  - 463 passed; one pre-existing Starlette TestClient deprecation warning.
- `python -m ruff check apps/api scripts`
  - Passed.
- `python -m compileall apps/api apps/web/src scripts`
  - Passed.
- `pnpm --filter @nodo/web build`
  - Initial attempt blocked because Node was not on `PATH`.
  - Passed after prepending the repository's established Codex Node runtime.
- `git diff --check`
  - Passed; Git reported line-ending conversion warnings only.
- `secret-guard` over every touched or created slice file
  - Three generic-entropy findings were manually verified as documentation
    paths, not secrets.
- Credential-shaped value scan over touched source, tests, contracts, evidence,
  and the generated web bundle
  - Passed: no credential-shaped values found.

## Residual Risks

- PostgreSQL transaction and locking behavior is covered structurally and by
  in-memory race tests, but was not exercised against a live PostgreSQL staging
  database in this slice.
- The client UI was build-validated and statically covered; no authenticated
  Telegram browser smoke was performed.
- No global reputation backfill is included.

## Confirmations

- No deploy.
- No production access.
- No migration.
- No written comments or marketplace ranking changes.
- No changes to credits, Base USDC, Zelle, intake, support, or admin behavior.
- No secrets added.
- No `READY_FOR_REAL_USE` declaration.
