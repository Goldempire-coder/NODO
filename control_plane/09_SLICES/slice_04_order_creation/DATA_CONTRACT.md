# DATA_CONTRACT.md

Authoritative data touched by this slice:

- orders
- order_state_events
- ads
- credit_wallets / credits_ledger only for release on cancel/expired-before-payment
- audit_logs

Slice 04 does not create a separate idempotency table. Slice 04 uses `orders.idempotency_key`.

## orders

Required columns for slice 04:

- id uuid primary key
- public_order_code text unique not null
- ad_id uuid not null FK ads(id)
- business_id uuid not null FK businesses(id)
- remitter_user_id uuid not null FK users(id)
- status text not null
- idempotency_key text nullable
- completion_reason text nullable
- cancel_reason text nullable
- dispute_reason text nullable
- amount_usd numeric/decimal not null
- rate_snapshot numeric/decimal not null
- amount_bs_calculated numeric/decimal not null
- business_name_snapshot text not null
- payment_method_snapshot text not null
- delivery_method_snapshot text not null
- min_amount_snapshot numeric/decimal not null
- max_amount_snapshot numeric/decimal not null
- payment_instructions_snapshot jsonb not null
- receiver_data_json jsonb not null
- payment_data_revealed_at timestamptz nullable
- payment_data_revealed_by uuid nullable
- payment_report_deadline_at timestamptz not null
- payment_report_extension_used_at timestamptz nullable
- extension_used boolean not null default false
- expires_at timestamptz not null
- business_response_warning_at timestamptz nullable
- business_response_deadline_at timestamptz nullable
- delivery_warning_at timestamptz nullable
- delivery_deadline_at timestamptz nullable
- auto_complete_warning_12h_at timestamptz nullable
- auto_complete_warning_23h_at timestamptz nullable
- auto_complete_at timestamptz nullable
- paid_reported_at timestamptz nullable
- payment_confirmed_at timestamptz nullable
- delivered_at timestamptz nullable
- completed_at timestamptz nullable
- created_at timestamptz not null
- updated_at timestamptz not null

## order_state_events

Required columns:

- id uuid primary key
- order_id uuid not null FK orders(id)
- from_status text nullable
- to_status text not null
- event_type text not null
- actor_user_id uuid nullable FK users(id)
- actor_role text nullable
- reason text nullable
- request_id text not null
- metadata_json jsonb nullable
- created_at timestamptz not null

## Constraints and indexes

- `orders.status` CHECK against official `order.status`.
- `orders.cancel_reason` CHECK against official cancel reasons when status = `cancelled`.
- `orders.amount_usd >= 20`.
- `orders.rate_snapshot > 0`.
- `orders.amount_bs_calculated > 0`.
- `orders.payment_method_snapshot` CHECK IN (`zelle`, `usdt_trc20`).
- `orders.delivery_method_snapshot` CHECK IN (`pago_movil_ve`).
- `orders.payment_report_deadline_at` and `orders.expires_at` required for `waiting_payment`.
- Partial unique index on `(remitter_user_id, idempotency_key)` where `idempotency_key is not null`.
- `orders(public_order_code)` unique.
- Indexes required by `04_DATA/INDEXES.md`.

## Sensitive data rules

- `payment_instructions_snapshot` is private and immutable.
- Create/detail/list responses must return masked/summary instruction data only.
- Full instructions are revealed in slice 05 via `GET /api/v1/orders/{id}/payment-instructions`.
- Do not store tokens, secrets, storage paths or full sensitive data in audit logs.

Builder must update migrations from this contract only after owner approves build.
