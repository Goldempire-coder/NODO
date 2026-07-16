# BUILDER_PROMPT.md

Build only `slice_19_base_usdc_usdt_credit_topups`.

Must read:

- `control_plane/03_DOMAIN_RULES/ONCHAIN_CREDIT_TOPUPS_MASTER.md`
- `control_plane/03_DOMAIN_RULES/CREDITS_AND_BILLING_MASTER.md`
- `control_plane/04_DATA/*`
- `control_plane/05_SECURITY/*`
- `control_plane/06_API_CONTRACTS/CREDITS_API.md`
- `control_plane/06_API_CONTRACTS/ERROR_CONTRACT.md`
- `control_plane/08_SCREENS/business/B-05_BUY_CREDITS.md`
- `control_plane/08_SCREENS/business/B-06_CREDIT_PAYMENT_PENDING.md`
- `control_plane/08_SCREENS/business/B-07_MY_CREDITS_LEDGER.md`
- this slice folder

Build:

- Base USDC credit purchase creation.
- On-chain tx verification by watcher and tx hash submit.
- Exact-once credit ledger/wallet accreditation.
- Admin read/reject for `under_review`.
- Tests/evidence/report.

Do not build:

- USDT Base.
- USDT TRC20 automatic crediting.
- Private key custody or signing.
- Refunds.
- Remittance custody.
- Deploy.
- READY_FOR_REAL_USE.
