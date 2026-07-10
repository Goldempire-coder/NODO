# STATE_CONTRACT.md

Official state behavior for this slice:

`payment_reported`, `payment_rejected`, `payment_confirmed` and `delivered`
can become `disputed`.

Slice 07 does not perform `delivered -> completed`, remitter confirmation,
rating or auto-complete. Those flows belong to a future slice.

## disputes.status

- open
- in_review
- resolved
- cancelled

Canonical transitions:

- open -> in_review
- open -> resolved
- in_review -> resolved
- open -> cancelled

Slice 07 build scope:

- creates `open` disputes only.
- may expose admin read-only list/detail.
- does not resolve disputes.
- does not complete or cancel orders from dispute resolution.

## Opening a dispute

Allowed previous order statuses:

- payment_reported
- payment_rejected
- payment_confirmed
- delivered

Effects:

- `orders.status = disputed`
- `orders.dispute_reason = reason`
- `disputes.previous_order_status = prior orders.status`
- `disputes.status = open`
- create `dispute_events.event_type = dispute_opened`
- audit `dispute_opened`

Credit/ad effects:

- From `payment_reported`: credits stay blocked, `ad.status = in_order`.
- From `payment_rejected`: credits stay blocked, `ad.status = in_order`.
- From `payment_confirmed`: credits already consumed, `ad.status = archived`.
- From `delivered`: credits already consumed, `ad.status = archived`.

## Admin resolution

Admin dispute resolution is not in slice 07.

Future admin resolution must define:

- required reason
- `resolution_type`
- whether final order state becomes `completed`, `cancelled` or remains `disputed`
- exact credit ledger effects
- exact `ad.status` effects
- audit events and notifications

Rules:

- No state outside 04_DATA/ENUMS_AND_STATUS_MASTER.md.
- All transitions go through a state machine/service.
- Transitions must validate actor, ownership, current state and allowed next state.
- State changes must create audit events.
- If a state conflict appears, stop with BLOCKED_BY_CONTRACT_CONFLICT.
