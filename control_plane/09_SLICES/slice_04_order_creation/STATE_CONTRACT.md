# STATE_CONTRACT.md

Official state behavior for this slice:

- `POST /api/v1/orders` persists `order.status = waiting_payment`.
- `created` is allowed only as audit/state event for order creation, not as the final persisted status of the create endpoint.
- Creating order moves `ad.status active -> in_order`.
- `waiting_payment` expires after 30 minutes.
- One extension of 15 minutes is allowed when `extension_used = false`.
- Cancel before payment report releases ad/credits according to contracts.

## Transitions in slice 04

- no order -> `waiting_payment`: create order from active ad.
- `waiting_payment -> waiting_payment`: extend deadline once.
- `waiting_payment -> cancelled`: remitter cancels before payment report.
- `waiting_payment -> cancelled`: passive/materialized expiration when deadline passes.

## Passive/materialized expiration

When a `waiting_payment` order is read or mutated after `payment_report_deadline_at`:

- set `order.status = cancelled`
- set `cancel_reason = payment_not_reported_in_time`
- if ad has not expired, set `ad.status = active`
- if ad expired, materialize `ad.status = expired`
- release blocked ad credits if applicable
- write state event
- audit cancellation/expiration

## Rules

- No state outside `04_DATA/ENUMS_AND_STATUS_MASTER.md`.
- All transitions go through a state machine/service.
- Transitions must validate actor, ownership, current state and allowed next state.
- State changes must create audit events and `order_state_events`.
- Slice 04 must not transition to `payment_reported`, `payment_confirmed`, `delivered`, `completed` or `disputed`.
- If a state conflict appears, stop with `BLOCKED_BY_CONTRACT_CONFLICT`.
