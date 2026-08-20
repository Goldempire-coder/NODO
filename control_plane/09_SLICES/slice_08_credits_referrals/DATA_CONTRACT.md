# DATA_CONTRACT.md

Datos canonicos tocados por `slice_08_credits_referrals`.

## Tablas activas

- credit_wallets
- credits_ledger
- credit_purchases
- referral_codes
- referral_events
- file_assets
- businesses founder fields
- audit_logs

## Modelos legacy/no validos

- `founder_access` como tabla activa: no valido en MVP. Founder usa campos en `businesses`.
- `referrals`: no valido para nuevas migraciones. Usar `referral_codes` y `referral_events`.

## credit_purchases

Columnas:

- id uuid primary key
- business_id uuid not null FK businesses(id)
- package_code text not null
- credits_amount integer not null
- price_usd numeric(12,2) not null
- payment_method text not null
- status text not null
- idempotency_key text nullable
- stripe_checkout_session_id text nullable
- stripe_payment_intent_id text nullable
- stripe_event_id text nullable
- manual_payment_reference text nullable
- manual_tx_hash text nullable
- manual_network text nullable
- proof_file_id uuid nullable FK file_assets(id)
- approved_by_admin_id uuid nullable FK users(id)
- rejected_by_admin_id uuid nullable FK users(id)
- admin_note text nullable
- created_at timestamptz not null
- updated_at timestamptz not null
- paid_at timestamptz nullable
- approved_at timestamptz nullable
- rejected_at timestamptz nullable
- failed_at timestamptz nullable
- expired_at timestamptz nullable

Constraints:

- package_code IN (`starter`, `pro`, `business`, `enterprise`)
- payment_method IN official `credit_purchase.payment_method`
- status IN official `credit_purchase.status`
- credits_amount > 0
- price_usd > 0
- Stripe purchase requires `stripe_checkout_session_id`
- Manual purchase requires `proof_file_id`
- Zelle manual requires `manual_payment_reference`
- USDT manual requires `manual_tx_hash` and `manual_network = TRC20`
- approved_at required when status = `approved`
- rejected_at and admin_note required when status = `rejected`
- paid_at required when status = `paid` or `approved` from Stripe

Indexes/unique:

- credit_purchases(business_id, status, created_at desc)
- credit_purchases(stripe_checkout_session_id) unique parcial when not null
- credit_purchases(stripe_event_id) unique parcial when not null
- credit_purchases(stripe_payment_intent_id) unique parcial when not null
- credit_purchases(manual_payment_reference) unique parcial when not null
- credit_purchases(business_id, idempotency_key) unique parcial when idempotency_key not null

## Manual proof file_assets

- resource_type = credit_purchase
- resource_id = credit_purchases.id
- file_type = credit_purchase_proof
- owner_user_id = business owner id
- MIME allowed: image/jpeg, image/png, image/webp, application/pdf
- max size: 5 MB
- storage privado obligatorio
- `storage_path` nunca se expone en API, frontend, logs ni audit metadata
- Admin/super_admin obtiene signed URL corta solo en endpoint autorizado futuro/admin detail, con reason y audit cuando aplique

## referral_codes

Columnas:

- id uuid primary key
- business_id uuid not null FK businesses(id)
- code text not null
- status text not null default active
- created_at timestamptz not null
- updated_at timestamptz not null
- disabled_at timestamptz nullable

Constraints/indexes:

- code unique
- business_id unique
- status IN (`active`, `disabled`)

## referral_events

Columnas:

- id uuid primary key
- referral_code_id uuid not null FK referral_codes(id)
- referrer_business_id uuid not null FK businesses(id)
- referred_business_id uuid not null FK businesses(id)
- related_credit_purchase_id uuid nullable FK credit_purchases(id)
- status text not null
- credits_awarded integer not null default 0
- reject_reason text nullable
- created_at timestamptz not null
- approved_at timestamptz nullable
- rewarded_at timestamptz nullable
- rejected_at timestamptz nullable

Constraints/indexes:

- referrer_business_id <> referred_business_id
- status IN (`pending`, `approved`, `rewarded`, `rejected`)
- credits_awarded >= 0
- unique referred_business_id where status in (`pending`, `approved`, `rewarded`)
- unique related_credit_purchase_id where related_credit_purchase_id is not null
- referral_events(referrer_business_id, created_at desc)
- referral_events(referred_business_id, created_at desc)

El flujo vigente por aprobacion mantiene `related_credit_purchase_id = null` y
usa `related_referral_id` en el ledger. El campo de compra queda solo para
compatibilidad historica.

## founder fields

Fuente canonica:

- businesses.founder_status
- businesses.founder_started_at
- businesses.founder_expires_at

Founder status:

- active
- expired
- revoked
- null = no founder access

## credits_ledger

Tipos oficiales:

- purchase
- founder_free_use
- referral_bonus
- hold
- release
- consume
- expire
- admin_adjustment

`refund` y `adjustment` son legacy/no validos. Build slice 08 debe agregar migracion que alinee el CHECK existente de `credits_ledger.type` al enum oficial antes de usar `referral_bonus`, `expire` o `admin_adjustment`.

Ledger append-only. Toda acreditacion debe validar doble grant por:

- credit_purchases.status
- stripe_event_id
- stripe_checkout_session_id
- related_credit_purchase_id
- reference_type/reference_id/type
- idempotency key
