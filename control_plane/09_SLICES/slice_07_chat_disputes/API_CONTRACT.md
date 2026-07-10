# API_CONTRACT.md

# API_CONTRACT.md

Endpoints authorized for this slice:

- GET /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/message-attachments
- POST /api/v1/orders/{id}/disputes
- GET /api/v1/admin/disputes
- GET /api/v1/admin/disputes/{id}

Endpoints explicitly not authorized in slice 07:

- POST /api/v1/admin/disputes/{id}/resolve
- POST /api/v1/orders/{id}/confirm-received
- POST /api/v1/orders/{id}/complete
- POST /api/v1/orders/{id}/rating

API rules:

- Use /api/v1 prefix unless project router defines equivalent grouping.
- Mutating endpoints require auth, RBAC, validation and audit when sensitive.
- Idempotency-Key is required for `POST /api/v1/orders/{id}/messages`,
  `POST /api/v1/orders/{id}/message-attachments` and
  `POST /api/v1/orders/{id}/disputes`.
- Responses must follow 06_API_CONTRACTS/ERROR_CONTRACT.md.
- Frontend cannot bypass backend permissions.

Global contracts:

- Message endpoints are governed by `06_API_CONTRACTS/MESSAGES_API.md`.
- Dispute endpoints are governed by `06_API_CONTRACTS/DISPUTES_API.md`.
- Admin dispute resolution is governed by `slice_09_admin_console`, not slice 07.

## GET /api/v1/orders/{id}/messages

Headers:

- Authorization: Bearer JWT

Permissions:

- Remitter can read messages only for own order.
- Business owner can read messages only for own business order.
- Admin/super_admin can read messages for dispute review.
- Support can read only when support view is explicitly enabled by RBAC.

Query:

- `cursor` optional.
- `limit` optional, 1..50, default 25.

Response:

```json
{
  "order_id": "uuid",
  "items": [
    {
      "id": "uuid",
      "sender_role": "remitter",
      "body": "safe sanitized text",
      "visibility": "parties",
      "status": "visible",
      "attachments": [
        {
          "id": "uuid",
          "file_asset_id": "uuid",
          "file_type": "message_attachment",
          "mime_type": "image/png",
          "size_bytes": 12345,
          "created_at": "timestamp"
        }
      ],
      "created_at": "timestamp"
    }
  ],
  "next_cursor": "opaque-or-null"
}
```

Forbidden fields:

- `storage_path`
- signed URLs
- full payment instructions
- `account_value`
- tokens/secrets

## POST /api/v1/orders/{id}/messages

Headers:

- Authorization: Bearer JWT
- Idempotency-Key: required

Request:

```json
{
  "body": "message text",
  "attachment_ids": ["uuid"]
}
```

Validation:

- `body` is required when `attachment_ids` is empty.
- `body` max length: 2000 characters.
- At most 5 attachments per message.
- Links/scripts/HTML must be sanitized or blocked by service policy.

Allowed order states:

- `payment_reported`
- `payment_rejected`
- `payment_confirmed`
- `delivered`
- `disputed`

Response:

```json
{
  "message": {
    "id": "uuid",
    "order_id": "uuid",
    "sender_role": "remitter",
    "body": "safe sanitized text",
    "visibility": "parties",
    "status": "visible",
    "attachments": [],
    "created_at": "timestamp"
  }
}
```

Audit:

- `message_created`
- `dispute_message_created` when the order is already `disputed`

Idempotency:

- Same key + same payload returns the same message.
- Same key + different payload returns `IDEMPOTENCY_PAYLOAD_MISMATCH`.

## POST /api/v1/orders/{id}/message-attachments

Headers:

- Authorization: Bearer JWT
- Idempotency-Key: required

Request:

- multipart/form-data with `file`.
- optional `purpose = message_attachment`.

Rules:

- Uses `file_assets`.
- `resource_type = message` while unattached files use pending message id or service-held pending id.
- `file_type = message_attachment`.
- Storage is private.
- Signed URLs are not persisted.
- `storage_path` is never returned.

Allowed MIME:

- image/jpeg
- image/png
- image/webp
- application/pdf

Max size:

- 5 MB.

Response:

```json
{
  "attachment": {
    "id": "uuid",
    "file_asset_id": "uuid",
    "file_type": "message_attachment",
    "mime_type": "image/png",
    "size_bytes": 12345,
    "created_at": "timestamp"
  }
}
```

Audit:

- `message_attachment_uploaded`

## POST /api/v1/orders/{id}/disputes

Headers:

- Authorization: Bearer JWT
- Idempotency-Key: required

Request:

```json
{
  "reason": "payment_mobile_not_received",
  "description": "safe text",
  "evidence_file_ids": ["uuid"]
}
```

Allowed actors:

- Remitter owner.
- Business owner of the order only when disputing a payment report rejection/correction scenario explicitly allowed by state policy.

Allowed order states:

- `payment_reported`
- `payment_rejected`
- `payment_confirmed`
- `delivered`

Effects:

- `orders.status = disputed`.
- `orders.dispute_reason = reason`.
- `disputes.previous_order_status` stores the prior order status.
- Creates `disputes.status = open`.
- Creates `dispute_events`.
- Audits `dispute_opened`.

Credit/ad effects:

- From `payment_reported`: credits stay blocked, `ad.status = in_order`.
- From `payment_rejected`: credits stay blocked, `ad.status = in_order`.
- From `payment_confirmed`: credits already consumed, `ad.status = archived`.
- From `delivered`: credits already consumed, `ad.status = archived`.

Response:

```json
{
  "dispute": {
    "id": "uuid",
    "order_id": "uuid",
    "status": "open",
    "reason": "payment_mobile_not_received",
    "previous_order_status": "delivered",
    "created_at": "timestamp"
  }
}
```

Idempotency:

- Same key + same payload returns the same dispute.
- Same key + different payload returns `IDEMPOTENCY_PAYLOAD_MISMATCH`.
- A second open dispute for the same order returns `DISPUTE_ALREADY_OPEN`.

## GET /api/v1/admin/disputes

Headers:

- Authorization: Bearer JWT

Permissions:

- admin/super_admin can list.
- support can list read-only if RBAC allows.

Query:

- `status` optional.
- `cursor` optional.
- `limit` optional, 1..50.

Response must be masked and must not include private storage keys, full account
values or signed URLs.

## GET /api/v1/admin/disputes/{id}

Headers:

- Authorization: Bearer JWT

Permissions:

- admin/super_admin can view.
- support can view read-only if RBAC allows.

Response includes order snapshot summary, dispute, dispute_events, message
metadata and attachment metadata. Full files require a future signed URL/view
contract and are not part of slice 07.

## Rate limits

- message list/read: per user + order + route.
- message create: per user + order + route.
- attachment upload: per user + order + route.
- dispute open: per user + order + route.
- admin dispute list/detail: per admin/support + route.

All limits return `RATE_LIMITED` with a safe error body.
