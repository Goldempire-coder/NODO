# CREDITS_AND_BILLING_MASTER.md

NODO sells listing/advertising credits to businesses.

NODO does not charge spread and does not charge commission on the exchange transaction between remitter and business.

## Credit packages

- Starter: 5 credits = $10
- Pro: 15 credits = $25
- Business: 50 credits = $75
- Enterprise: 200 credits = $250

## Cost per ad

- $20-$100 = 1 credit
- $100-$500 = 2 credits
- $500-$2,000 = 3 credits

Required credits are calculated from ad.amount_max_usd.

## Ad lifetime

- One active ad lasts 7 days from activation.
- If it does not produce a completed transaction within 7 days, it expires.
- Reactivating a paused ad does not require a new credit because the original hold remains attached.
- Republishing an archived or expired ad requires available credits and creates a new 7-day listing.
- If an ad expires while an order is already active, the order continues; the expired ad cannot accept new orders.

## Credit consumption rule

Credits are listing/advertising credits. They are blocked when the business publishes the ad and consumed when the business confirms payment received or when the 7-day listing expires without a completed transaction.

- Publishing a $20-$100 ad blocks 1 credit.
- Publishing a $100-$500 ad blocks 2 credits.
- Publishing a $500-$2,000 ad blocks 3 credits.
- More than $2,000 is not available in MVP or requires manual review.
- Clicking an ad does not consume credits.
- Creating an order does not consume extra credits.
- Business payment confirmation consumes the blocked credits.
- If the order expires or is cancelled before payment confirmation and the ad is still inside its 7-day lifetime, blocked credits remain attached to the ad and the ad returns to `active`.
- If the ad reaches 7 days without payment confirmation, blocked credits are consumed with ledger `expire` and the ad is archived.
- Reusing an archived or expired ad as a template must first verify available credits, then create a new hold for the new listing.
- NODO still does not receive, hold, transfer or process user funds.

## Wallet accounting

The wallet must track three counters:

- available_credits
- blocked_credits
- consumed_credits

### Publish ad

```txt
available_credits: 15
blocked_credits: 0

Publish $100-$500 ad
Cost: 2 credits

available_credits: 13
blocked_credits: 2
```

Ledger entry: `hold`.

### Order expires or cancels before payment confirmation while ad is still alive

```txt
available_credits: 13
blocked_credits: 2

Order expired or cancelled before payment confirmation

available_credits: 13
blocked_credits: 2
```

Ledger entry: none. The original ad hold remains.

### Ad reaches 7 days without completed transaction

```txt
available_credits: 13
blocked_credits: 2
consumed_credits: 0

Ad expires without completed transaction

available_credits: 13
blocked_credits: 0
consumed_credits: 2
```

Ledger entry: `expire`.

### Business confirms payment received

```txt
available_credits: 13
blocked_credits: 2
consumed_credits: 0

Business confirms payment received

available_credits: 13
blocked_credits: 0
consumed_credits: 2
```

Ledger entry: `consume`.

The ad moves to archived because it already fulfilled its function.

In `slice_06_business_order_ops`, business payment confirmation must set:

```txt
ad.status = archived
```

The order remains alive for delivery, dispute or future close flows, but the ad publication must not return to the marketplace.

## Order hold rule

The order hold protects availability and prevents curious users from costing businesses credits.

- Opening/clicking an ad creates no hold.
- Creating an order creates a temporary availability hold.
- Creating an order does not create an additional credit debit or consume credits.
- If no payment report is submitted before the order timer expires, the order expires and the ad returns to `active` if the 7-day lifetime has not ended.
- If that same ad has already reached 7 days, the ad is archived and the listing credit is consumed with ledger `expire`.
- If payment is reported, the hold stays until confirmation or dispute resolution according to the state machine.
- Reporting payment in `slice_05_payment_instructions_reports` does not consume credits.
- Credits remain blocked while order is `payment_reported`.
- If the business reports a payment problem, the order enters `disputed` and
  credits remain blocked until Admin resolution. Historical
  `payment_rejected` orders retain the same blocked-credit treatment while they
  are escalated.
- Credit consumption happens when the business confirms payment received or when the listing reaches 7 days without completed transaction.
- Repeated abandoned orders are controlled by remitter cooldowns/rate limits.

## Order timers and credit impact

| Order state | Timer | Result | Credit impact |
| --- | --- | --- | --- |
| waiting_payment | 30 min + one 15 min extension | cancelled, cancel_reason = payment_not_reported_in_time | keep original ad hold if ad is still alive; consume with `expire` if ad reached 7 days |
| payment_reported | 2h warning / 6h dispute | disputed, dispute_reason = business_no_payment_confirmation | keep credits blocked |
| payment_rejected | legacy/historical recovery | escalate to disputed | keep credits blocked |
| payment_confirmed | 30 min warning / 2h dispute | disputed, dispute_reason = business_confirmed_payment_but_not_delivered | credits already consumed |
| delivered | 24h auto-close if no dispute | completed, completion_reason = auto_completed_after_24h | no new credit movement |

Credit consumption does not happen when the remitter clicks, creates the order, or reports payment. It happens when the business confirms payment received or when the 7-day listing expires without completed transaction.

## Dispute impact

Opening a dispute in `slice_07_chat_disputes` does not create credit ledger
movements.

- Dispute from `payment_reported`: credits remain blocked, `ad.status = in_order`.
- Dispute from `payment_rejected`: credits remain blocked, `ad.status = in_order`.
- Dispute from `payment_confirmed`: credits already consumed, `ad.status = archived`.
- Dispute from `delivered`: credits already consumed, `ad.status = archived`.

Admin resolution is contracted in `slice_09_admin_console`.

Credit effects by `resolution_type`:

| resolution_type | Dispute origin | Credit effect |
| --- | --- | --- |
| remitter_favored | `payment_reported` or `payment_rejected` | consume blocked credits with ledger `consume`, reason `admin_dispute_resolution_consume` |
| remitter_favored | `payment_confirmed` or `delivered` | no new movement; credits were already consumed |
| business_favored | `payment_reported` or `payment_rejected` | consume blocked credits with ledger `consume`, reason `admin_dispute_resolution_consume` |
| business_favored | `payment_confirmed` or `delivered` | no new movement; credits were already consumed |
| cancelled | `payment_reported` or `payment_rejected` | release blocked credits with ledger `release`, reason `admin_dispute_resolution_release` |
| cancelled | `payment_confirmed` or `delivered` | no automatic refund in MVP; admin adjustment requires separate audited adjustment contract |
| completed | `payment_reported` or `payment_rejected` | consume blocked credits with ledger `consume`, reason `admin_dispute_resolution_consume` |
| completed | `payment_confirmed` or `delivered` | no new movement; credits were already consumed |
| keep_under_review | any | no movement |

Rules:

- Slice 07 must not invent credit resolution behavior.
- Slice 09 must prevent duplicate consume/release for the same dispute resolution.
- Wallet balances must never become negative.
- All credit movements must be append-only ledger entries plus audit logs.

## Founder businesses

- Founder rules live in `control_plane/03_DOMAIN_RULES/FOUNDER_RULES.md`.
- Founder uses canonical fields on `businesses`: `founder_status`, `founder_started_at`, `founder_expires_at`.
- `founder_access` table is legacy/no valid for MVP.
- 30 days free from `founder_started_at`.
- Must pass business verification before use.
- Always respects risk limits, max order amount and RBAC.
- Free period does not remove audit, limits or suspension rules.
- Publishing during active founder period does not charge credits, but must write `founder_free_use`.

## Payment methods for buying credits

Primary:

- stripe_checkout

Manual fallbacks:

- zelle_manual_admin_approved
- usdt_manual_admin_approved

On-chain primary from slice 19:

- base_usdc_onchain

Rules:

- `base_usdc_onchain` is the canonical on-chain credit topup flow.
- Base mainnet is the only real network: `chain_id = 8453`.
- USDC Base official contract: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- USDT Base is not active in MVP because no official Tether Base contract is verified in the canonical docs.
- `usdt_manual_admin_approved` remains legacy/manual TRC20 and must not be treated as Base.
- Full on-chain rules live in `control_plane/03_DOMAIN_RULES/ONCHAIN_CREDIT_TOPUPS_MASTER.md`.

## Stripe flow

1. Business selects credit package.
2. Backend creates credit_purchase with status pending_payment.
3. Backend creates Stripe Checkout session.
4. Business pays in Stripe Checkout.
5. Stripe webhook confirms payment.
6. Backend verifies webhook signature.
7. Backend marks credit_purchase paid/approved.
8. Backend writes credits_ledger purchase.
9. Backend sends notification to business.

Stripe webhook is the source of truth for automatic crediting.

Never credit from frontend success redirect alone.

Stripe accreditation must be idempotent and block double credit by:

- `stripe_event_id`
- `stripe_checkout_session_id`
- purchase status
- ledger reference
- idempotency key where applicable

Stripe secrets must never appear in frontend, repository, logs or API responses.

## Zelle manual flow

1. Business selects credit package.
2. Backend creates credit_purchase with status pending_manual_review.
3. UI shows official NODO Zelle instructions.
4. Business uploads proof.
5. Admin approves/rejects with note.
6. If approved, backend writes credits_ledger purchase.

Manual proof contract:

- Use `file_assets.resource_type = credit_purchase`.
- Use `file_assets.resource_id = credit_purchases.id`.
- Use `file_assets.file_type = credit_purchase_proof`.
- Storage is private.
- Signed URL is short-lived and only for authorized admin/super_admin review.
- `storage_path` is never exposed in API, frontend, logs or audit metadata.
- Admin approve/reject requires reason.

## USDT manual flow

1. Business selects credit package.
2. Backend creates credit_purchase with status pending_manual_review.
3. UI shows official NODO USDT wallet/network.
4. Business submits TxID/hash and optional screenshot.
5. Admin verifies and approves/rejects with note.
6. If approved, backend writes credits_ledger purchase.

## Referrals

Referral rules live in `control_plane/03_DOMAIN_RULES/REFERRALS_MASTER.md`.

Canonical model:

- `referral_codes`
- `referral_events`

Legacy/no valid:

- `referrals` table for new migrations/contracts.

Referral bonus is credited only through `credits_ledger.type = referral_bonus` after the referred business qualifies. Self-referral and double bonus are prohibited.

For referral qualification, a first credit purchase qualifies when:

- Stripe/manual legacy purchase has `credit_purchases.status = approved`.
- Base USDC on-chain purchase has `credit_purchases.status = credited`.
- The purchase has exactly one `credits_ledger.type = purchase` linked by `related_credit_purchase_id`.

On-chain statuses before `credited` do not qualify referral bonuses.

## Credit ledger types

- purchase
- founder_free_use
- referral_bonus
- hold
- release
- consume
- expire
- admin_adjustment

Legacy/no valid active types:

- refund
- adjustment

Use `release` for releases/refunds of holds and `admin_adjustment` for admin corrections.

## Credit ledger canonical schema

Cada movimiento en `credits_ledger` debe guardar:

- id
- business_id
- type
- amount
- balance_available_before
- balance_available_after
- balance_blocked_before
- balance_blocked_after
- balance_consumed_before
- balance_consumed_after
- related_ad_id
- related_order_id nullable
- related_referral_id nullable
- related_credit_purchase_id nullable
- reason
- source
- reference_type
- reference_id
- notes nullable
- created_by
- created_at

`reason` es obligatorio y explica el movimiento. `notes` es opcional y solo agrega contexto; no reemplaza `reason`.

Para `slice_03_ads_marketplace`:

- publicar anuncio genera `hold` cuando no aplica founder access.
- `hold` usa `reference_type = ad` y `reference_id = related_ad_id`.
- si el wallet no existe para un negocio aprobado, slice 03 puede crearlo lazy/idempotente con balances cero.
- crear wallet no acredita creditos.
- si no hay creditos disponibles ni founder access vigente, publicar responde `CREDIT_BALANCE_INSUFFICIENT`.

## Required audit events

- credit_purchase_created
- stripe_checkout_started
- stripe_payment_succeeded
- stripe_payment_failed
- manual_credit_payment_submitted
- manual_credit_payment_approved
- manual_credit_payment_rejected
- onchain_credit_purchase_created
- onchain_tx_hash_submitted
- onchain_payment_detected
- onchain_payment_confirmations_pending
- onchain_payment_verified
- onchain_credit_purchase_credited
- onchain_payment_under_review
- onchain_payment_rejected
- onchain_payment_verification_failed
- onchain_tx_duplicate_detected
- onchain_watcher_run_started
- onchain_watcher_run_finished
- onchain_watcher_run_failed
- credits_added
- credits_held
- credits_released
- credits_consumed
- ad_expired
- admin_credit_adjustment

## Prohibited

- no transaction commission in MVP
- no crediting from unverified Stripe redirect
- no manual approval without admin note
- no negative credit balance unless explicitly approved later
- no direct DB credit mutation outside credits service
- no double credit consumption for the same order
- no credit release when a business reports a payment problem or a historical `payment_rejected` order is escalated
- no crediting from Stripe redirect
- no exposing manual proof `storage_path`
- no using `founder_access` table as active MVP model
- no using `referrals` table as active MVP model
- no accepting Base tokens by symbol/name only
- no accepting USDT Base in MVP
- no storing private keys or seed phrases for credit topups
- no crediting on-chain purchases without verifier + ledger transaction

