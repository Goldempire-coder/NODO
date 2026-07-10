# SCOPE.md

## Objective

Registrar negocios y permitir aprobacion/rechazo admin con evidencia y auditoria.

## Included

Legacy note after slice 14B1:
- The owner-side onboarding endpoints below remain historical/compatibility contracts for slice 02.
- They are not active Mini App Negocio self-onboarding.
- Mini App Negocio access is governed by `slice_14B1_business_access_control_contracts` and `GET /api/v1/surface/session`.

- businesses
- business_verification_submissions
- business_payment_methods
- file_assets for private verification documents
- audit_logs
- POST /api/v1/businesses
- PUT /api/v1/businesses/{id}
- POST /api/v1/businesses/{id}/verification-documents
- POST /api/v1/businesses/{id}/submit-verification
- GET /api/v1/businesses/me
- GET /api/v1/admin/businesses/pending
- GET /api/v1/admin/businesses/{id}
- POST /api/v1/admin/businesses/{id}/verification-documents/{file_id}/view-url
- POST /api/v1/admin/businesses/{id}/approve
- POST /api/v1/admin/businesses/{id}/reject

## Affected screens

- B-01_BUSINESS_ONBOARDING
- B-02_BUSINESS_VERIFICATION_FORM
- B-03_VERIFICATION_PENDING
- A-02_PENDING_BUSINESSES
- A-03_BUSINESS_VERIFICATION_DETAIL

## Explicitly excluded

- ad creation
- orders
- credit purchase
- dispute resolution

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.
