# DATA_CONTRACT.md

Authoritative data touched by this slice:

- `payment_reports`
- `file_assets`
- `orders`
- `order_state_events`
- `audit_logs`

Slice 05 does not create `payment_evidence_files`.

Slice 05 does not create `storage_objects`.

## payment_reports

Required columns:

- id uuid primary key
- order_id uuid not null FK orders(id)
- reported_by_user_id uuid not null FK users(id)
- status text not null default `submitted`
- idempotency_key text nullable
- payment_type text not null
- payment_reference text nullable
- payment_sender_name text nullable
- payment_sender_account_masked text nullable
- tx_hash text nullable
- network text nullable
- payment_amount numeric/decimal not null
- proof_file_id uuid nullable FK file_assets(id)
- report_payload_hash text nullable
- admin_notes text nullable
- created_at timestamptz not null
- updated_at timestamptz not null

## payment_reports constraints

- `payment_reports.order_id` FK orders(id).
- `payment_reports.reported_by_user_id` FK users(id).
- `payment_reports.status` CHECK IN (`submitted`, `corrected`, `rejected`, `accepted`).
- Slice 05 only creates `submitted`.
- `payment_reports.payment_type` CHECK IN (`zelle`, `usdt_trc20`).
- `payment_reports.payment_amount > 0`.
- Zelle requires:
  - `payment_reference` not null
  - `payment_sender_name` not null
  - `proof_file_id` not null
- USDT TRC20 requires:
  - `tx_hash` not null
  - `network = TRC20`
- Unique partial index: one active/submitted payment report per `order_id`.
- Unique partial index: `(reported_by_user_id, idempotency_key)` where `idempotency_key is not null`.
- `proof_file_id` must belong to same order/payment report and owner; service must enforce this.

## file_assets for payment evidence

Use existing `file_assets`.

Rules:

- `file_assets.resource_type = payment_report`
- `file_assets.resource_id = payment_reports.id`
- `file_assets.file_type = payment_evidence`
- `file_assets.owner_user_id = orders.remitter_user_id`
- `storage_path` not null and private
- `storage_path` never exposed in API public responses, frontend, logs or audit metadata
- allowed mime types:
  - `image/jpeg`
  - `image/png`
  - `image/webp`
  - `application/pdf`
- max size: `5242880`

Pre-report evidence upload rule:

- `POST /payment-evidence` may reserve a future `payment_reports.id` as `pending_payment_report_id`.
- It stores `file_assets.resource_type = payment_report` and `file_assets.resource_id = pending_payment_report_id`.
- `POST /payment-report` must create `payment_reports.id = pending_payment_report_id` when using that proof.
- Service must validate proof ownership, order ownership and idempotency before creating the report.

## orders touched

Slice 05 may update:

- `payment_data_revealed_at`
- `payment_data_revealed_by`
- `status`
- `paid_reported_at`
- `business_response_warning_at`
- `business_response_deadline_at`
- `updated_at`

Slice 05 must not modify immutable snapshots:

- amount_usd
- rate_snapshot
- amount_bs_calculated
- business_name_snapshot
- payment_method_snapshot
- delivery_method_snapshot
- min_amount_snapshot
- max_amount_snapshot
- payment_instructions_snapshot
- receiver_data_json

## order_state_events

Required event for report:

- from_status: `waiting_payment`
- to_status: `payment_reported`
- event_type: `payment_reported`
- actor_user_id: remitter id
- actor_role: `remitter`
- request_id required
- metadata must not include full payment instructions, full account values, raw storage paths or secrets

## Sensitive data rules

- Full `account_value` may be returned only by `GET /api/v1/orders/{id}/payment-instructions` to the owner.
- `tx_hash` may be stored internally but UI/list/audit must mask/truncate.
- `payment_reference` and sender account are masked outside the owner/report detail context.
- Audit logs must not contain full payment instructions, storage paths, tokens or secrets.
