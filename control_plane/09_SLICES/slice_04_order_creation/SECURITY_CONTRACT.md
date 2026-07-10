# SECURITY_CONTRACT.md

Security requirements for `slice_04_order_creation`.

## Auth and RBAC

- Auth is mandatory for all order endpoints.
- Actor for create/list/detail/cancel/extend in slice 04: `remitter` with active user status.
- Guest cannot create, list, view, cancel or extend orders.
- Backend enforces RBAC; frontend hiding is not a defense.

## Ownership

- Remitter can create an order only for an eligible active ad.
- Remitter can view, cancel and extend only own orders.
- Business owner read/operation of incoming orders belongs to slice 06 unless a later contract explicitly adds read-only support.
- Permission errors must not leak private resource existence.

## Sensitive data

- Create/detail/list responses must not reveal full payment instructions.
- Create/detail/list responses must not reveal `account_value`, private storage paths, business documents, Telegram IDs, secrets or internal-only fields.
- `payment_instructions_snapshot` may be persisted privately for the order, but full reveal belongs to slice 05.
- Receiver data is sensitive; mask it in list responses and avoid logging full values.

## Rate limits

Apply backend rate limits to:

- `POST /api/v1/orders`
- `GET /api/v1/orders/{id}`
- `GET /api/v1/orders/mine`
- `POST /api/v1/orders/{id}/extend-payment-deadline`
- `POST /api/v1/orders/{id}/cancel`

Dimensions should include user, IP, route/action and order/ad where applicable.

## Idempotency

- `POST /api/v1/orders` requires `Idempotency-Key`.
- Cancel and extend require `Idempotency-Key`.
- Same key + same payload returns the same result.
- Same key + different payload returns `IDEMPOTENCY_CONFLICT` or canonical idempotency mismatch error.

## Audit

Required audit for mutating actions:

- `order_created`
- `ad_moved_in_order`
- `order_cancelled`
- `payment_deadline_extended`
- passive expiration/cancel event when materialized

Audit logs must not contain full payment instructions, account values, receiver sensitive data, tokens or secrets.

If any control is missing, stop with `BLOCKED_BY_SECURITY_GAP`.
