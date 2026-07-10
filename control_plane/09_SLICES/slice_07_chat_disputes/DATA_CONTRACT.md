# DATA_CONTRACT.md

Authoritative data touched by this slice:

- messages
- message_attachments
- disputes
- dispute_events
- orders
- audit_logs

Rules:

- Use migrations, not manual DB edits.
- Add constraints and indexes for every hot query.
- Never store money/tasa values as float.
- Sensitive fields must be masked in admin/UI where full value is not required.
- Every state-changing record must be traceable through audit_logs or state events.

`chat_messages` is a legacy/non-valid table name for this slice. Builders must
use `messages`.

## messages

- id uuid primary key
- order_id uuid not null FK orders(id)
- sender_user_id uuid not null FK users(id)
- sender_role text not null
- body text nullable
- visibility text not null default `parties`
- status text not null default `visible`
- idempotency_key text nullable
- created_at timestamptz not null
- updated_at timestamptz not null
- deleted_at timestamptz nullable

Rules:

- `sender_role` CHECK IN (`remitter`, `business_owner`, `admin`, `super_admin`, `support`).
- `visibility` CHECK IN (`parties`, `admin_only`).
- `status` CHECK IN (`visible`, `hidden`, `deleted`).
- Either `body` or at least one attachment is required by service.
- `body` max length is 2000 characters.
- No raw HTML/scripts; UI must render sanitized text.
- Unique partial `(sender_user_id, idempotency_key)` when `idempotency_key is not null`.

## message_attachments

- id uuid primary key
- message_id uuid nullable FK messages(id)
- order_id uuid not null FK orders(id)
- file_asset_id uuid not null FK file_assets(id)
- uploaded_by_user_id uuid not null FK users(id)
- file_type text not null default `message_attachment`
- mime_type text not null
- size_bytes integer not null
- status text not null default `active`
- created_at timestamptz not null
- updated_at timestamptz not null
- deleted_at timestamptz nullable

Rules:

- Uses `file_assets` with private storage.
- `file_assets.resource_type = message`.
- `file_assets.file_type = message_attachment`.
- Allowed MIME: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- `size_bytes <= 5242880`.
- `storage_path` is never exposed in API, frontend, audit metadata or logs.
- Pending attachments may have `message_id = null` until message creation attaches them.
- Service must validate owner/order before attaching file to message.

## disputes

- id uuid primary key
- order_id uuid not null FK orders(id)
- opened_by_user_id uuid not null FK users(id)
- opened_by_role text not null
- previous_order_status text not null
- reason text not null
- description text nullable
- status text not null default `open`
- resolution_type text nullable
- resolution_reason text nullable
- resolved_by_admin_id uuid nullable FK users(id)
- created_at timestamptz not null
- updated_at timestamptz not null
- resolved_at timestamptz nullable
- cancelled_at timestamptz nullable

Rules:

- One open/in_review dispute per order.
- `status` CHECK IN (`open`, `in_review`, `resolved`, `cancelled`).
- `reason` CHECK against `order.dispute_reason`.
- `previous_order_status` must be one of `payment_reported`, `payment_rejected`, `payment_confirmed`, `delivered`.
- Resolution fields are reserved for `slice_09_admin_console`; slice 07 does not mutate them.

## dispute_events

- id uuid primary key
- dispute_id uuid not null FK disputes(id)
- order_id uuid not null FK orders(id)
- actor_user_id uuid not null FK users(id)
- actor_role text not null
- event_type text not null
- old_status text nullable
- new_status text nullable
- reason text nullable
- metadata_json jsonb nullable
- created_at timestamptz not null

Rules:

- Append-only.
- `event_type` CHECK IN (`dispute_opened`, `dispute_status_changed`, `dispute_note_added`, `dispute_resolved`, `dispute_cancelled`).
- Slice 07 creates `dispute_opened`; resolution events belong to `slice_09_admin_console`.

Builder must update 04_DATA/DATA_MODEL_MASTER.md, DATABASE_CONSTRAINTS.md and INDEXES.md if implementation needs fields not listed here.
