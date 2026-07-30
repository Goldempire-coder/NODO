# API Contract

## POST /api/v1/orders/{order_id}/payment-report

- Requires an active remitter who owns the order and an `Idempotency-Key`.
- Locks the order and accepts only non-expired `waiting_payment`.
- `payment_amount` must equal `orders.amount_usd`.
- `payment_type` and network are canonicalized before persistence.
- USDT TRC20 `tx_hash` must be 64 hexadecimal characters; an optional `0x`
  prefix is accepted and removed before lowercase persistence.
- A canonical `(network, tx_hash)`, proof file ID, and proof content SHA-256
  cannot be reused.
- Uploaded proof files are bound to the `order_id` where they were created; a
  proof from another order returns `INVALID_PAYMENT_EVIDENCE`.
- Report, order transition, state event, and audit entry commit together.
- A competing committed transition returns `ORDER_STATE_CONFLICT`.

## POST /api/v1/orders/{order_id}/cancel

- Requires the owning remitter and an `Idempotency-Key`.
- Locks the order and accepts only non-expired `waiting_payment` without a
  submitted report.
- If payment instructions were revealed, the locked transition requires
  `payment_not_sent_confirmed=true`.
- Order cancellation, capacity release, ad restoration, state event, and audit
  entry commit together.
- PostgreSQL restores a valid ad or archives an expired ad and consumes its
  credit hold inside the same transaction.
- Replay returns the stored result and does not repeat effects.

## GET /api/v1/orders/{order_id}/payment-instructions

- Locks the order before marking payment instructions as revealed.
- Serializes with cancellation so cancellation without confirmation and reveal
  cannot both succeed.
- The view audit commits with the reveal marker before full instructions are
  returned.

## POST /api/v1/business/orders/{order_id}/cannot-attend

- Requires the active owner of the order business, accepted terms, unlocked
  business PIN, and an `Idempotency-Key`.
- Accepts no free-form reason.
- Accepts only non-expired `waiting_payment` without a submitted report.
- Persists `status=cancelled` and `cancel_reason=business_unavailable`.
- Releases capacity, restores the ad when still valid, records safe events, and
  enqueues one generic client notification after commit.

## Errors

- `ORDER_STATE_CONFLICT` (`409`): another terminal or payment transition won.
- `PAYMENT_REPORT_AMOUNT_MISMATCH` (`409`): reported amount differs from order.
- `PAYMENT_REPORT_PROOF_ALREADY_USED` (`409`): canonical hash, proof identity,
  proof file, or proof content hash already belongs to a report.
- Existing ownership, auth, expiration, PIN, and idempotency errors remain.
