# SCOPE.md

## Objective

Compra/acreditacion de creditos publicitarios, wallet, ledger, Stripe, pagos manuales Zelle/USDT, historial Founder sin exencion y referrals. Owner 2026-09-29: creditos iniciales por asignacion administrativa normal.

## Included

- credit_wallets
- credits_ledger
- credit_purchases
- referral_codes
- referral_events
- founder fields in businesses (`founder_status`, `founder_started_at`, `founder_expires_at`)
- file_assets para comprobantes manuales de credit purchase
- audit_logs
- GET /api/v1/business/credits/wallet
- GET /api/v1/business/credits/ledger
- POST /api/v1/business/credits/stripe-checkout
- POST /api/v1/webhooks/stripe
- POST /api/v1/business/credits/manual-payment
- GET /api/v1/business/referrals
- POST /api/v1/business/referrals/apply
- GET /api/v1/admin/credit-purchases
- POST /api/v1/admin/credit-purchases/{id}/approve
- POST /api/v1/admin/credit-purchases/{id}/reject
- POST /api/v1/admin/credits/adjust

## Affected screens

Pantallas canonicas existentes:

- B-04_BUSINESS_DASHBOARD: dashboard de negocio con resumen de creditos.
- B-05_BUY_CREDITS: comprar creditos.
- B-06_CREDIT_PAYMENT_PENDING: subir/ver comprobante manual.
- B-07_MY_CREDITS_LEDGER: wallet/ledger.
- B-15_REFERRAL_PROGRAM: referrals.
- A-04_PENDING_CREDIT_PAYMENTS: admin pending credit payments.
- A-05_CREDIT_PAYMENT_DETAIL: admin credit payment detail.
- A-13_MANUAL_ADJUSTMENTS: admin credit adjustments.

Nombres no canonicos del prompt quedan mapeados asi y no deben crearse como pantallas nuevas:

- B-04_CREDITS_DASHBOARD -> B-04_BUSINESS_DASHBOARD
- B-06_PAYMENT_PROOF -> B-06_CREDIT_PAYMENT_PENDING
- B-07_REFERRALS -> B-15_REFERRAL_PROGRAM
- A-04_CREDIT_PAYMENTS -> A-04_PENDING_CREDIT_PAYMENTS

## Explicitly excluded

- customer remittance funds
- escrow
- automatic Zelle processing
- changes to ads/orders credit consumption already built
- jobs masivos
- admin completo fuera de creditos
- slice 09

If a requested change falls outside this scope, stop and report `BLOCKED_BY_SCOPE_EXPANSION`.
