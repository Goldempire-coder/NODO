# SCOPE.md

## Objective

Panel admin funcional completo para negocios, pagos manuales, disputas, usuarios,
metricas y auditoria, sin reconstruir superficies ya entregadas por slices
anteriores.

## Included

- admin dashboard
- negocios y verificacion admin
- credit_purchases como composicion de slice 08
- disputas admin con resolucion contratada en slice 09
- ordenes en vista admin
- usuarios/remitentes en vista admin
- audit_logs
- metricas como read model calculado desde tablas existentes
- GET /api/v1/admin/dashboard
- GET /api/v1/admin/businesses
- GET /api/v1/admin/businesses/{id}
- GET /api/v1/admin/businesses/pending
- POST /api/v1/admin/businesses/{id}/approve
- POST /api/v1/admin/businesses/{id}/reject
- GET /api/v1/admin/orders
- GET /api/v1/admin/orders/{id}
- GET /api/v1/admin/credit-purchases
- POST /api/v1/admin/credit-purchases/{id}/approve
- POST /api/v1/admin/credit-purchases/{id}/reject
- POST /api/v1/admin/credits/adjust
- GET /api/v1/admin/disputes
- GET /api/v1/admin/disputes/{id}
- POST /api/v1/admin/disputes/{id}/resolve
- GET /api/v1/admin/audit-logs
- GET /api/v1/admin/metrics

Admin role/user mutation is allowed only if implemented under the explicit
`ADMIN_API.md` role-management contract and restricted to `super_admin`.

## Affected screens

- A-01_ADMIN_DASHBOARD
- A-02_PENDING_BUSINESSES
- A-03_BUSINESS_VERIFICATION_DETAIL
- A-06_DISPUTES_LIST
- A-07_DISPUTE_DETAIL
- A-08_EVASION_REPORTS
- A-09_BUSINESS_RISK_DETAIL
- A-10_USERS_REMITTERS
- A-11_AUDIT_LOGS
- A-12_SYSTEM_METRICS

Slice 09 may link to or compose these slice 08-owned screens, but must not take
ownership or rebuild their business logic:

- A-04_PENDING_CREDIT_PAYMENTS
- A-05_CREDIT_PAYMENT_DETAIL
- A-13_MANUAL_ADJUSTMENTS

## Explicitly excluded

- admin-only Telegram whitelist as sole control
- direct DB mutations
- unaudited exports
- slice 10 jobs, auto-complete and notification workers
- ratings
- escrow, protected funds or guaranteed delivery claims
- automatic Zelle processing
- rebuilding slice 08 credit payment/manual adjustment flows

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.
