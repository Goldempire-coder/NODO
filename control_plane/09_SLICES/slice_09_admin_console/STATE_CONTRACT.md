# STATE_CONTRACT.md

Official state behavior for this slice:

Admin can approve/reject/suspend businesses, approve/reject manual credit
payments, resolve disputes and perform audited adjustments only through official
state machines.

## Dispute resolution state contract

`POST /api/v1/admin/disputes/{id}/resolve` is active in slice 09.

`POST /api/v1/admin/orders/{id}/open-dispute` adds the only direct Admin action
from `payment_rejected`: an atomic `payment_rejected -> disputed` transition.
It creates the dispute and timelines without changing capacity, credits or ad
state. Direct Admin transitions from `payment_rejected` to `cancelled` or
`payment_confirmed` are prohibited.

Allowed actors:

- `admin`
- `super_admin`

Forbidden actor:

- `support` can view only and cannot resolve.

Preconditions:

- `disputes.status in ('open', 'in_review')`.
- `orders.status = disputed`.
- `Idempotency-Key` is required.
- `reason` is required.

Resolution effects:

| resolution_type | dispute.status | order.status | credit effect | ad.status |
| --- | --- | --- | --- | --- |
| remitter_favored | resolved | cancelled with `cancel_reason = admin_cancelled` | consume blocked credits if previous status was `payment_reported` or `payment_rejected`; no extra movement if already consumed | archived |
| business_favored | resolved | completed with `completion_reason = admin_resolved` | consume blocked credits if previous status was `payment_reported` or `payment_rejected`; no extra movement if already consumed | archived |
| cancelled | cancelled | cancelled with `cancel_reason = admin_cancelled` | release blocked credits if previous status was `payment_reported` or `payment_rejected`; no automatic refund if credits were already consumed | archived |
| completed | resolved | completed with `completion_reason = admin_resolved` | consume blocked credits if previous status was `payment_reported` or `payment_rejected`; no extra movement if already consumed | archived |
| keep_under_review | in_review | disputed | no credit movement | unchanged from dispute origin |

Credit movements must use `credits_ledger`:

- `consume` with `reason = admin_dispute_resolution_consume` when blocked credits are consumed.
- `release` with `reason = admin_dispute_resolution_release` when blocked credits are released.
- No wallet balance can become negative.
- No duplicate ledger movement is allowed for the same dispute resolution.

NODO does not receive, hold, transfer or guarantee funds. Admin dispute
resolution only records an operational decision inside NODO.

## Production atomicity gate

Status: `READY_FOR_VALIDATOR_REVIEW`.

Administrative dispute opening and terminal PostgreSQL dispute resolution must
be durable transaction boundaries. Terminal resolution updates order/capacity,
dispute, credit/ad and audit records in one database transaction; participant
notifications are emitted only after the committed state exists. PostgreSQL
regression coverage must continue to prove that terminal resolutions archive
the ad and move blocked credits exactly once.

Rules:

- No state outside 04_DATA/ENUMS_AND_STATUS_MASTER.md.
- All transitions go through a state machine/service.
- Transitions must validate actor, ownership, current state and allowed next state.
- State changes must create audit events.
- If a state conflict appears, stop with BLOCKED_BY_CONTRACT_CONFLICT.
