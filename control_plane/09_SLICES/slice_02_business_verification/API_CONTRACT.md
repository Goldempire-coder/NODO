# API_CONTRACT.md

Endpoints authorized for this slice:

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

Slice 14B1 precedence:
- `POST /api/v1/businesses`, verification document upload and submit-verification are not active Mini App Negocio self-onboarding.
- `GET /api/v1/businesses/me` is not the Business Mini App access gate.
- Mini App Negocio must use `GET /api/v1/surface/session` and `business_access_links` as defined by `slice_14B1_business_access_control_contracts`.

API rules:

- Use `/api/v1` prefix.
- All routes require auth except existing health/auth routes from previous slices.
- Mutating endpoints require auth, RBAC, validation, rate limit and audit when sensitive.
- `Idempotency-Key` is required for create, update, submit, approve and reject.
- Responses must follow `06_API_CONTRACTS/ERROR_CONTRACT.md`.
- Frontend cannot bypass backend permissions.
- Payloads and responses are governed by `06_API_CONTRACTS/BUSINESSES_API.md` and `06_API_CONTRACTS/ADMIN_API.md`.

## Business owner endpoints

### POST /api/v1/businesses

- Legacy/internal after slice 14B1.
- Runtime real must not allow public self-onboarding from Mini App Cliente, Mini App Negocio or generic authenticated API usage.
- Active runtime response for public use: `403 BUSINESS_SELF_ONBOARDING_DISABLED`.
- Business creation for new merchants must come through Bot Registro Negocios + Admin Web flow.
- Any controlled internal/test fixture path must remain outside product surfaces and cannot grant Mini App Negocio access.

### PUT /api/v1/businesses/{id}

- Legacy/internal after slice 14B1/P0.2.
- Runtime real must not allow public owner-side business mutation.
- Active runtime response for public use: `403 BUSINESS_SELF_ONBOARDING_DISABLED`.
- Future business settings/profile editing requires a separate governed contract.

### POST /api/v1/businesses/{id}/verification-documents

- Legacy/internal after slice 14B1/P0.2.
- Runtime real must not allow public owner-side verification uploads.
- Active runtime response for public use: `403 BUSINESS_SELF_ONBOARDING_DISABLED`.
- Business intake documents use Bot Registro Negocios + `file_assets.resource_type = business_intake`.

### POST /api/v1/businesses/{id}/submit-verification

- Legacy/internal after slice 14B1/P0.2.
- Runtime real must not allow public owner-side verification submit.
- Active runtime response for public use: `403 BUSINESS_SELF_ONBOARDING_DISABLED`.
- Business verification submission for referred merchants is reviewed through Bot Registro Negocios + Admin Web flow.

### GET /api/v1/businesses/me

- Returns own business with sensitive fields masked by default.

## Admin endpoints

### GET /api/v1/admin/businesses/pending

- Cursor pagination.
- Returns masked list.
- Admin/super_admin/support can view according to RBAC.

### GET /api/v1/admin/businesses/{id}

- Returns verification detail.
- Support sees metadata/masked data; admin/super_admin can request document signed URL.

### POST /api/v1/admin/businesses/{id}/verification-documents/{file_id}/view-url

- Admin/super_admin only.
- Reason required.
- Signed URL expires in <= 300 seconds.
- Audits `verification_document_viewed`.

### POST /api/v1/admin/businesses/{id}/approve

- Admin/super_admin only.
- Only when business is `pending`.
- Reason required.
- Updates business to `approved`, latest submission to `approved`, sets `approved_at`.
- Audits `business_approved`.

### POST /api/v1/admin/businesses/{id}/reject

- Admin/super_admin only.
- Only when business is `pending`.
- Reason required.
- Updates business to `rejected`, latest submission to `rejected`, stores `admin_reason`.
- Audits `business_rejected`.

## Errors

- UNAUTHENTICATED
- FORBIDDEN
- VALIDATION_ERROR
- NOT_FOUND
- CONFLICT
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- BUSINESS_NOT_FOUND
- BUSINESS_ALREADY_EXISTS
- BUSINESS_ALREADY_SUBMITTED
- BUSINESS_STATUS_INVALID
- BUSINESS_VERIFICATION_REQUIRED
- BUSINESS_DOCUMENT_REQUIRED
- BUSINESS_DOCUMENT_INVALID
- BUSINESS_DOCUMENT_NOT_FOUND
- ADMIN_REASON_REQUIRED
