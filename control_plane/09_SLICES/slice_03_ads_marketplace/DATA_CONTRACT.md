# DATA_CONTRACT.md

Authoritative data touched by this slice:

- ads
- credit_wallets
- credits_ledger
- audit_logs
- businesses read
- business_payment_methods read

## ads

Columns required:

- id uuid primary key
- business_id uuid not null FK businesses(id)
- payment_method_id uuid not null FK business_payment_methods(id)
- payment_method text not null
- delivery_method text not null
- rate_bs_per_usd numeric(18,6) not null
- amount_min_usd numeric(12,2) not null
- amount_max_usd numeric(12,2) not null
- required_credits integer not null
- status text not null default `active`
- credit_hold_ledger_id uuid nullable FK credits_ledger(id)
- credit_consumed_ledger_id uuid nullable FK credits_ledger(id)
- created_at timestamptz not null
- updated_at timestamptz not null
- activated_at timestamptz nullable
- expires_at timestamptz nullable
- rate_updated_at timestamptz nullable

Constraints/indexes:

- `business_id` FK `businesses(id)`.
- `payment_method_id` FK `business_payment_methods(id)`.
- `status` CHECK IN (`draft`, `active`, `in_order`, `paused`, `expired`, `archived`, `suspended`).
- `payment_method` CHECK IN (`zelle`, `usdt_trc20`).
- `delivery_method` CHECK IN (`pago_movil_ve`).
- `amount_min_usd >= 20`.
- `amount_max_usd >= amount_min_usd`.
- `amount_max_usd <= 2000` in MVP unless future manual review contract exists.
- `rate_bs_per_usd > 0`.
- `required_credits IN (1, 2, 3)` for MVP active ads.
- `activated_at` and `expires_at` required when `status in ('active', 'paused', 'in_order')`.
- `expires_at = activated_at + 7 days` at publish; pausing never changes it.
- Partial unique index prevents overlapping active/paused ads for same business, payment method, delivery method and amount range.
- index `ads(status, payment_method, delivery_method, rate_bs_per_usd desc)`.
- index `ads(status, payment_method, delivery_method, amount_min_usd, amount_max_usd)`.
- index `ads(business_id, status, created_at desc)`.
- index `ads(expires_at)`.
- partial index for `status = 'active'`.

Rules:

- Public marketplace reads only effective active, non-expired ads from approved businesses.
- `draft` is allowed enum but UI in slice 03 publishes directly; persistent draft editing is future/internal unless explicitly approved.
- `in_order` is set by slice_04 when order creation is built.
- Admin/suspension flows are not implemented in this slice unless an admin endpoint is later approved.
- Every state change goes through ad state machine/service.
- No direct DB state mutation from routes.

## credit_wallets

Columns required:

- id uuid primary key
- business_id uuid not null unique FK businesses(id)
- available_credits integer not null default 0
- blocked_credits integer not null default 0
- consumed_credits integer not null default 0
- lifetime_purchased_credits integer not null default 0
- lifetime_bonus_credits integer not null default 0
- lifetime_adjusted_credits integer not null default 0
- updated_at timestamptz not null

Constraints/indexes:

- `business_id` unique FK businesses(id).
- all counters `>= 0`.
- balance can never become negative.
- index `credit_wallets(business_id)` unique.

Creation rule:

- Slice 03 creates `credit_wallets` lazily and idempotently for approved businesses when missing, before validating publish.
- New lazy wallet starts with zero balances.
- Missing wallet must not create fake credits.
- If publish cannot proceed due insufficient balance, return `CREDIT_BALANCE_INSUFFICIENT`, including historical Founder businesses.

## credits_ledger

Canonical schema:

- id uuid primary key
- business_id uuid not null FK businesses(id)
- type text not null
- amount integer not null
- balance_available_before integer not null
- balance_available_after integer not null
- balance_blocked_before integer not null
- balance_blocked_after integer not null
- balance_consumed_before integer not null
- balance_consumed_after integer not null
- related_ad_id uuid nullable FK ads(id)
- related_order_id uuid nullable FK orders(id)
- related_referral_id uuid nullable FK referrals(id)
- related_credit_purchase_id uuid nullable FK credit_purchases(id)
- reason text not null
- source text not null
- reference_type text not null
- reference_id uuid not null
- notes text nullable
- created_by uuid nullable FK users(id)
- created_at timestamptz not null

Rules:

- `notes` is optional additional context. It does not replace `reason`.
- Ledger is append-only.
- `type` CHECK IN official `credits_ledger.type`.
- `amount > 0`.
- `hold` requires `related_ad_id`, `reference_type = 'ad'`, `reference_id = related_ad_id`.
- `release` requires prior hold not consumed/released and `related_ad_id`.
- `consume` requires `related_ad_id`, `related_order_id` and payment confirmation from future order flow.
- Slice 03 creates `hold` on publish and creates `release` only when materializing expiration without active order/payment.
- `balance_*_after` must equal previous balance plus/minus movement.
- No negative balances.
- index `credits_ledger(business_id, created_at desc)`.
- index `credits_ledger(type, created_at desc)`.
- index `credits_ledger(reference_type, reference_id, created_at desc)`.
- partial unique index for active hold per `related_ad_id` where `type = 'hold'`.

## audit_logs

Required events in this slice:

- ad_created
- ad_published
- ad_updated
- ad_paused
- ad_archived
- ad_expired
- credits_held
- credits_released when passive expiration releases a hold

Rules:

- Use `resource_type/resource_id`.
- Include `request_id`.
- Include old/new state for state changes.
- Include idempotency key metadata when relevant.
- Do not store full payment account values, storage paths, tokens, secrets or private business documents.
