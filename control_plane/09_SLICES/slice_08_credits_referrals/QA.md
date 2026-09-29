# QA.md

Required QA:

- wallet own business only.
- ledger own business only.
- Stripe checkout creates pending_payment and does not credit wallet.
- Stripe redirect/frontend success does not credit wallet.
- Stripe webhook invalid signature rejects.
- Stripe webhook success credits exactly once.
- Duplicate Stripe event does not double credit.
- Duplicate checkout/session does not double credit.
- Manual payment creates pending_manual_review and does not credit wallet.
- Manual payment requires proof.
- Manual proof uses private file_assets and never exposes `storage_path`.
- Admin approve manual payment requires reason.
- Admin approve credits exactly once and writes ledger purchase.
- Admin reject requires reason and does not credit.
- Admin adjustment requires reason, RBAC and audit.
- support cannot approve/reject/adjust.
- wallet balances never negative.
- historical Founder status never bypasses the normal publication credit hold.
- manual admin credits support publication and confirmation with idempotent consumption.
- referral self-referral blocked.
- referral duplicate blocked.
- referral cap 20 enforced.
- referral bonus writes ledger `referral_bonus`.
- lowercase/uppercase/whitespace referral code normalizes in intake.
- Admin approval awards referrer 5 and referred business 0.
- approval replay/concurrency writes one referral event and one ledger.
- partial award cannot exceed cap 20.
- later credit purchase does not duplicate referral bonus.
- no `refund` or `adjustment` ledger type used as active enum.
- frontend build.
- runners 00-08.
- backend pytest acumulado.
- ruff.
- compileall.
- frontend secret/private scan.

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.
