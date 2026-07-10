# DATA_CONTRACT.md

Authoritative data touched by this slice:

- businesses
- business_verification_submissions
- business_payment_methods
- file_assets
- audit_logs

## businesses

Columns required:

- id uuid primary key
- owner_user_id uuid not null FK users(id)
- business_name text not null after create
- rif text nullable before submit, required before submit-verification
- address text nullable before submit, required before submit-verification
- phone text nullable before submit, required before submit-verification
- country text not null default `VE`
- verification_status text not null default `pending`
- trust_level text not null default `new`
- risk_level text not null default `normal`
- max_order_amount_usd numeric(12,2) not null default 100.00
- daily_limit_usd numeric(12,2) not null default 300.00
- active_order_limit integer not null default 1
- rating_avg numeric(4,2) nullable
- completed_orders_count integer not null default 0
- disputes_count integer not null default 0
- evasion_reports_count integer not null default 0
- referral_code text nullable
- referral_credits_earned integer not null default 0
- founder_status text nullable
- founder_started_at timestamptz nullable
- founder_expires_at timestamptz nullable
- created_at timestamptz not null
- updated_at timestamptz not null
- approved_at timestamptz nullable

Constraints/indexes:

- `businesses.owner_user_id` FK users(id).
- `businesses.verification_status` CHECK IN (`pending`, `approved`, `rejected`, `suspended`, `blocked`).
- `businesses.trust_level` CHECK IN (`new`, `basic`, `plus`, `pro`, `premium`).
- `businesses.risk_level` CHECK IN (`normal`, `watch`, `under_review`, `restricted`, `high_risk`).
- `businesses.approved_at` only when `verification_status = approved`.
- monetary/risk limits use numeric/integers, never float.
- index `businesses(owner_user_id)`.
- index `businesses(verification_status, created_at desc)`.
- index `businesses(verification_status, risk_level)`.
- index `businesses(business_name)` or normalized equivalent.

Rules:

- `draft` is UI/workflow only and is not persisted as `business.verification_status`.
- Pending review is represented only by `pending`.
- `under_review` is `risk_level`, not `verification_status`.
- Owner cannot set approval, trust/risk levels or limits.
- Admin approve/reject must go through service/state machine and audit.

## business_verification_submissions

Columns required:

- id uuid primary key
- business_id uuid not null FK businesses(id)
- submitted_by_user_id uuid not null FK users(id)
- status text not null default `pending`
- submitted_data_json jsonb not null
- admin_reviewed_by_user_id uuid nullable FK users(id)
- admin_reason text nullable
- submitted_at timestamptz not null
- reviewed_at timestamptz nullable
- created_at timestamptz not null
- updated_at timestamptz not null

Constraints/indexes:

- `status` CHECK IN (`pending`, `approved`, `rejected`).
- `admin_reason` required when `status = rejected`.
- `reviewed_at` required when `status in ('approved', 'rejected')`.
- `admin_reviewed_by_user_id` required when `status in ('approved', 'rejected')`.
- unique partial pending submission per business.
- index `business_verification_submissions(business_id, status, created_at desc)`.
- index `business_verification_submissions(status, submitted_at desc)`.
- index `business_verification_submissions(admin_reviewed_by_user_id, reviewed_at desc)` when reviewed_by is not null.

Rules:

- `submitted_data_json` is a snapshot of submitted fields and `document_file_ids`; it must not contain storage paths, secrets or signed URLs.
- Every status change must be traceable through `audit_logs`.
- Admin rejection stores `admin_reason`.
- Approval/rejection updates both submission status and business `verification_status`.

## business_payment_methods

This slice creates base payment-method records only when included in the verification payload. It does not publish ads or reveal payment instructions to remitters.

Columns required:

- id uuid primary key
- business_id uuid not null FK businesses(id)
- method_type text not null
- network text nullable
- account_value text not null
- account_masked text not null
- holder_name text not null
- verified_status text not null default `pending`
- active boolean not null default false
- created_at timestamptz not null
- updated_at timestamptz not null

Constraints/indexes:

- `method_type` CHECK IN (`zelle`, `usdt_trc20`).
- `network` must be null for `zelle` and `trc20` for `usdt_trc20`.
- `verified_status` CHECK IN (`pending`, `approved`, `rejected`).
- index `business_payment_methods(business_id, active)`.
- index `business_payment_methods(business_id, method_type, network)`.

Rules:

- `account_value` is sensitive.
- UI/admin lists show `account_masked` by default.
- No ad creation or public payment instruction reveal in this slice.

## file_assets for verification documents

Slice 02 includes private uploads for verification documents.

Columns used from `file_assets`:

- id uuid primary key
- owner_user_id uuid not null FK users(id)
- resource_type text not null
- resource_id uuid not null
- file_type text not null
- storage_path text not null
- mime_type text not null
- size_bytes integer not null
- created_at timestamptz not null
- deleted_at timestamptz nullable

Constraints/indexes:

- `resource_type = 'business'` for this slice.
- `resource_id` references `businesses.id`.
- `file_type` CHECK IN (`rif_document`, `business_license`, `owner_identity`, `address_proof`).
- `mime_type` CHECK IN (`image/jpeg`, `image/png`, `image/webp`, `application/pdf`).
- `size_bytes <= 5242880`.
- index `file_assets(resource_type, resource_id, created_at desc)`.
- index `file_assets(owner_user_id, created_at desc)`.

Rules:

- Files live in private storage.
- `storage_path` is never returned to frontend.
- Full document access uses short signed URL and audit event.
- `verification_document_uploaded` audit event is required on upload.
- `verification_document_viewed` audit event is required when admin opens a signed URL.

## audit_logs

Required events:

- business_created
- business_updated
- business_submitted
- business_approved
- business_rejected
- payment_method_added
- verification_document_uploaded
- verification_document_viewed

Rules:

- Use `resource_type/resource_id`.
- Include `request_id`.
- Admin sensitive actions require `reason`.
- Do not store documents, storage paths, signed URLs, full payment data, tokens or secrets.
