# DATA_CONTRACT.md

Authoritative data touched by this slice.

## users base

Columns required:

- id uuid primary key
- telegram_id bigint unique nullable until auth slice finalizes
- username text nullable
- first_name text nullable
- last_name text nullable
- phone text nullable
- role text not null default `remitter`
- status text not null default `active`
- trust_level text nullable
- orders_created_count integer not null default 0
- orders_completed_count integer not null default 0
- orders_expired_count integer not null default 0
- created_at timestamptz not null
- updated_at timestamptz not null
- last_seen_at timestamptz nullable

Constraints/indexes:

- `users.telegram_id` unique when not null.
- `users.role` CHECK against `ENUMS_AND_STATUS_MASTER.md`.
- `users.status` CHECK against `ENUMS_AND_STATUS_MASTER.md`.
- index `users(status, created_at desc)`.
- index `users(role, status)`.

## audit_logs base

Columns required:

- id uuid primary key
- actor_user_id uuid nullable FK users(id)
- actor_role text nullable
- event_type text not null
- resource_type text not null
- resource_id uuid nullable
- old_value_json jsonb nullable
- new_value_json jsonb nullable
- reason text nullable
- request_id text not null
- job_id uuid nullable
- ip_hash text nullable
- user_agent text nullable
- metadata_json jsonb nullable
- created_at timestamptz not null

Constraints/indexes:

- audit logs are append-only.
- index `audit_logs(resource_type, resource_id, created_at desc)`.
- index `audit_logs(actor_user_id, created_at desc)`.
- index `audit_logs(event_type, created_at desc)`.
- index `audit_logs(created_at desc)`.

## job_runs base

Columns required:

- id uuid primary key
- job_type text not null
- status text not null
- lock_key text nullable
- attempts integer not null default 0
- started_at timestamptz nullable
- finished_at timestamptz nullable
- error_code text nullable
- error_message_safe text nullable
- metadata_json jsonb nullable
- created_at timestamptz not null
- updated_at timestamptz not null

Constraints/indexes:

- index `job_runs(job_type, status, created_at desc)`.
- index `job_runs(lock_key)` partial when lock_key is not null.

## migrations metadata

Use the migration table required by the selected migration tool. Do not invent a custom migration table if Alembic/Supabase tooling already provides one.

## health metadata

Use `app_metadata` only for stable build/version metadata:

- id uuid primary key
- key text unique not null
- value_json jsonb not null
- created_at timestamptz not null
- updated_at timestamptz not null

Do not store every health check result in DB in MVP.

## Rules

- Use migrations, not manual DB edits.
- Add constraints and indexes for every hot query.
- Never store money/rate values as float.
- Sensitive fields must be masked in admin/UI where full value is not required.
- Every state-changing record must be traceable through audit_logs or state events.

Builder must update `04_DATA/DATA_MODEL_MASTER.md`, `DATABASE_CONSTRAINTS.md` and `INDEXES.md` if implementation needs fields not listed here.

