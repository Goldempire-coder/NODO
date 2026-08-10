# DISPUTES_API.md

Contrato API canonico para apertura, vista admin y resolucion admin de disputas.

Slice 07 no incluye resolucion admin de disputas. El endpoint
`POST /api/v1/admin/disputes/{id}/resolve` queda fuera de slice 07.

Slice 09 (`slice_09_admin_console`) si incluye resolucion admin de disputas con
el contrato definido en este archivo.

RBAC:

- admin/super_admin/support can view disputes according to RBAC.
- support is read-only.
- admin/super_admin cannot resolve disputes in slice 07.
- admin/super_admin can resolve disputes in slice 09.
- support cannot resolve disputes.

## Endpoints

- POST /api/v1/orders/{id}/disputes
- GET /api/v1/admin/disputes
- GET /api/v1/admin/disputes/{id}
- POST /api/v1/admin/orders/{id}/open-dispute
- POST /api/v1/admin/disputes/{id}/resolve

## Reglas comunes

- Requiere Authorization Bearer JWT.
- Requiere RBAC backend.
- Permission errors must not leak private resource existence.
- Rate limit obligatorio.
- No exponer `storage_path`, signed URLs, full payment instructions, `account_value`, tokens ni secretos.
- NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos.

## POST /api/v1/orders/{id}/disputes

Headers:

- Idempotency-Key required.

Request:

```json
{
  "reason": "payment_not_received_or_incomplete",
  "description": "safe text",
  "evidence_file_ids": ["uuid"]
}
```

Allowed actors:

- Remitter owner.
- Business owner for its own business order.
- Both participants may open from each allowed previous order state below.
- For a business actor in `payment_reported`, the visible action is `Reportar
  problema con pago` and the required structured reason is
  `payment_not_received_or_incomplete`.

Allowed previous order statuses:

- payment_reported
- payment_rejected (legacy/historical recovery only)
- payment_confirmed
- delivered

Effects:

- `orders.status = disputed`
- `orders.dispute_reason = reason`
- `disputes.previous_order_status = previous status`
- `disputes.status = open`
- creates `dispute_events.event_type = dispute_opened`
- audits `dispute_opened`
- From `payment_reported`, opening the business payment-problem dispute keeps
  `payment_reports.status = submitted`; it does not accept or reject the
  client's claim before Admin resolution.

Credit/ad effects:

- From `payment_reported`: credits stay blocked, `ad.status = in_order`.
- From `payment_rejected`: credits stay blocked, `ad.status = in_order`.
- From `payment_confirmed`: credits already consumed, `ad.status = archived`.
- From `delivered`: credits already consumed, `ad.status = archived`.

Capacity/completion effects:

- Operational capacity remains reserved while `orders.status = disputed`.
- A dispute in `open|in_review` blocks manual and automatic completion.
- Terminal admin resolution consumes capacity for `completed` or releases it
  for `cancelled`, exactly once.

Response:

```json
{
  "dispute": {
    "id": "uuid",
    "order_id": "uuid",
    "status": "open",
    "reason": "payment_not_received_or_incomplete",
    "previous_order_status": "payment_reported",
    "created_at": "timestamp"
  }
}
```

Idempotency:

- Same key + same payload returns same dispute and never duplicates state,
  events, audit or notifications.
- Same key + different payload returns IDEMPOTENCY_PAYLOAD_MISMATCH.
- Existing open/in_review dispute returns DISPUTE_ALREADY_OPEN.

Errors:

- ORDER_NOT_FOUND
- ORDER_NOT_OWNED
- ORDER_STATUS_INVALID
- DISPUTE_ALREADY_OPEN
- DISPUTE_NOT_ALLOWED
- DISPUTE_REASON_REQUIRED
- MESSAGE_ATTACHMENT_INVALID
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- FORBIDDEN
- RATE_LIMITED
- UNAUTHENTICATED
- VALIDATION_ERROR

## GET /api/v1/admin/disputes

Permissions:

- admin/super_admin can list.
- support can list read-only when RBAC allows.

Query:

- `status` optional.
- `cursor` optional.
- `limit` optional, 1..50.

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "order_id": "uuid",
      "public_order_code": "NODO-...",
      "status": "open",
      "reason": "payment_mobile_not_received",
      "previous_order_status": "delivered",
      "created_at": "timestamp"
    }
  ],
  "next_cursor": "opaque-or-null"
}
```

Errors:

- FORBIDDEN
- RATE_LIMITED
- UNAUTHENTICATED

## GET /api/v1/admin/disputes/{id}

Permissions:

- admin/super_admin can view.
- support can view read-only when RBAC allows.

Response:

```json
{
  "dispute": {
    "id": "uuid",
    "order_id": "uuid",
    "status": "open",
    "reason": "payment_mobile_not_received",
    "description": "safe text",
    "previous_order_status": "delivered",
    "created_at": "timestamp"
  },
  "order_summary": {
    "public_order_code": "NODO-...",
    "status": "disputed",
    "amount_usd": "100.00"
  },
  "events": [],
  "messages": []
}
```

Forbidden fields:

- `storage_path`
- signed URLs
- full payment instructions
- `account_value`
- tokens/secrets

Errors:

- DISPUTE_NOT_FOUND
- FORBIDDEN
- RATE_LIMITED
- UNAUTHENTICATED

## POST /api/v1/admin/orders/{id}/open-dispute

Purpose:

- Open an administrative investigation for a historical order stuck in
  `payment_rejected`; final resolution continues through the existing dispute
  endpoint. New business actions must not produce this state.

Permissions:

- active `admin` or `super_admin` only.
- `support`, client and business participants cannot invoke this admin action.

Request controls:

- `Idempotency-Key` required.
- non-empty `reason` required, maximum 500 characters.
- order must currently be `payment_rejected`.

Atomic effects:

- creates exactly one `disputes.status = open` record with
  `previous_order_status = payment_rejected`;
- persists the structured dispute reason as `other`; the explicit Admin reason
  remains in the dispute description, timelines and append-only audit;
- moves `orders.status` to `disputed`;
- creates `dispute_opened` in dispute and order timelines;
- appends audit `admin_order_dispute_opened` with actor, reason and request id;
- does not release or consume capacity, credits or the ad;
- notifies client and business with generic state copy after the committed
  transition;
- does not permit direct cancellation, payment confirmation or evidence
  resubmission.

Idempotency and concurrency:

- Same key plus same payload returns the stored response without duplicate
  dispute, events, audit or notifications.
- Same key plus different payload returns `IDEMPOTENCY_PAYLOAD_MISMATCH`.
- Concurrent distinct requests compete on the locked order state; exactly one
  can transition from `payment_rejected`.

Errors include `IDEMPOTENCY_KEY_REQUIRED`, `ORDER_NOT_FOUND`, `FORBIDDEN`,
`ORDER_STATUS_INVALID`, `DISPUTE_ALREADY_OPEN`,
`IDEMPOTENCY_PAYLOAD_MISMATCH` and `RATE_LIMITED`.

## POST /api/v1/admin/disputes/{id}/resolve

Slice owner:

- `slice_09_admin_console`

Headers:

- Authorization: Bearer `<session_jwt>`
- Idempotency-Key required.
- X-Request-Id required or generated by backend.

Permissions:

- admin can resolve.
- super_admin can resolve.
- support is read-only and must receive `FORBIDDEN`.

Request:

```json
{
  "resolution_type": "remitter_favored",
  "reason": "Evidence reviewed by admin",
  "notes": "Optional internal safe note"
}
```

Allowed `resolution_type`:

- remitter_favored
- business_favored
- cancelled
- completed
- keep_under_review

Rules:

- `reason` is required and stored in audit logs/dispute events.
- Dispute must have `status in ('open', 'in_review')`.
- Order must have `status = disputed`.
- State, credit and ad effects are defined by
  `03_DOMAIN_RULES/DISPUTE_RESOLUTION_MASTER.md`.
- PostgreSQL terminal resolution must update order/capacity, dispute,
  credit/ad and audit records in one database transaction.
- Participant notifications are emitted only after that transaction commits.
- Must create `dispute_events`.
- Terminal resolutions audit `dispute_resolved`.
- `keep_under_review` audits `dispute_marked_in_review`.
- No real money is moved. NODO does not receive, hold, transfer or guarantee funds.
- No response may expose `storage_path`, signed URLs, full payment instructions,
  `account_value`, tokens or secrets.
- A terminal resolution to `completed|cancelled` for an order with non-null
  `paid_reported_at` must extend the business publication pause to at least
  `database_now + 15 minutes` in the same terminal transaction. This cooldown
  does not alter the resolution's credit, capacity or ad outcome and does not
  override Admin restrictions.

Response:

```json
{
  "data": {
    "dispute": {
      "id": "uuid",
      "status": "resolved",
      "resolution_type": "remitter_favored",
      "resolved_at": "timestamp"
    },
    "order": {
      "id": "uuid",
      "public_order_code": "NODO-...",
      "status": "cancelled"
    },
    "credit_effect": {
      "type": "consume",
      "amount": 2,
      "ledger_id": "uuid-or-null"
    },
    "ad": {
      "id": "uuid",
      "status": "archived"
    }
  },
  "request_id": "req_..."
}
```

Idempotency:

- Same key + same payload returns the same result.
- Same key + different payload returns `IDEMPOTENCY_PAYLOAD_MISMATCH`.
- A terminal dispute cannot be resolved again except as idempotent replay.
- Duplicate credit ledger movement for the same dispute resolution is prohibited.

Rate limit:

- Required by actor, route, dispute_id and IP.

Errors:

- UNAUTHENTICATED
- FORBIDDEN
- DISPUTE_NOT_FOUND
- DISPUTE_STATUS_INVALID
- DISPUTE_RESOLUTION_NOT_ALLOWED
- DISPUTE_RESOLUTION_REASON_REQUIRED
- ORDER_STATUS_INVALID
- ADMIN_REASON_REQUIRED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- RATE_LIMITED
- VALIDATION_ERROR
