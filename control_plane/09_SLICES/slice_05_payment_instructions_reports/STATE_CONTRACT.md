# STATE_CONTRACT.md

Official state behavior for this slice:

```txt
waiting_payment -> payment_reported
```

## Payment instructions reveal

`GET /api/v1/orders/{id}/payment-instructions`:

- requires `order.status = waiting_payment`
- requires order not expired
- sets `payment_data_revealed_at` only if null
- sets `payment_data_revealed_by`
- audits `payment_instructions_viewed`
- does not create payment report
- does not change `order.status`

## Payment report transition

`POST /api/v1/orders/{id}/payment-report`:

- requires `order.status = waiting_payment`
- rejects expired order
- creates `payment_reports.status = submitted`
- sets `orders.status = payment_reported`
- sets `orders.paid_reported_at`
- sets business response warning/deadline fields according to order lifecycle contract
- creates `order_state_events`
- audits `payment_reported`

## After payment_reported

- Order must not be auto-cancelled by waiting-payment deadline.
- `ad.status` remains `in_order`.
- Credits remain blocked.
- Credit consumption waits for business confirmation in slice 06.
- Business confirmation/rejection is outside slice 05.
- Delivery, chat, dispute and jobs are outside slice 05.

## Invalid states

Block payment report when order is:

- `cancelled`
- `payment_reported` unless idempotent replay applies
- `payment_confirmed`
- `delivered`
- `completed`
- `disputed`

Rules:

- No state outside `04_DATA/ENUMS_AND_STATUS_MASTER.md`.
- All transitions go through state machine/service.
- Transitions validate actor, ownership, current state and allowed next state.
- State changes create audit events and `order_state_events`.
- If a state conflict appears, stop with `BLOCKED_BY_CONTRACT_CONFLICT`.
