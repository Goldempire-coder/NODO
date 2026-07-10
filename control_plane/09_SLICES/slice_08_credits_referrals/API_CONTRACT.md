# API_CONTRACT.md

Endpoints autorizados para `slice_08_credits_referrals`.

Todas las rutas activas usan `/api/v1`.

## Business

- GET /api/v1/business/credits/wallet
- GET /api/v1/business/credits/ledger
- POST /api/v1/business/credits/stripe-checkout
- POST /api/v1/business/credits/manual-payment
- GET /api/v1/business/referrals
- POST /api/v1/business/referrals/apply

## Webhook

- POST /api/v1/webhooks/stripe

## Admin

- GET /api/v1/admin/credit-purchases
- POST /api/v1/admin/credit-purchases/{id}/approve
- POST /api/v1/admin/credit-purchases/{id}/reject
- POST /api/v1/admin/credits/adjust

## Rutas legacy prohibidas

- GET /credits/balance
- GET /credits/ledger
- POST /credit-purchases
- POST /credit-purchases/:id/manual-proof
- POST /webhooks/stripe sin `/api/v1`
- GET /admin/credit-purchases sin `/api/v1`

## Reglas API

- Mutaciones requieren auth, RBAC, state validation, ownership, idempotencia y audit.
- Stripe webhook no usa auth JWT, pero requiere firma Stripe valida.
- Redirect frontend de Stripe nunca acredita creditos.
- Manual payment crea compra `pending_manual_review`; solo approve admin acredita.
- Responses siguen `06_API_CONTRACTS/ERROR_CONTRACT.md`.
- Payloads/responses detallados viven en `06_API_CONTRACTS/CREDITS_API.md`.
- Frontend no decide permisos ni balances.
