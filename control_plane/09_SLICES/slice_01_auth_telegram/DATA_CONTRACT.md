# DATA_CONTRACT.md

Authoritative data touched by this slice:

- users
- sessions
- audit_logs

## users updates

Slice 01 finalizes Telegram identity:

- `users.telegram_id` is required for authenticated Telegram-created users.
- `users.telegram_id` remains unique.
- `users.last_seen_at` updates on successful login.
- `users.username`, `first_name`, `last_name` may update from verified Telegram initData.
- `users.role` defaults to `remitter` for new users.
- `users.status` defaults to `active` for new users.
- Do not expose `telegram_id` in public API responses.

## sessions

Columns required:

- id uuid primary key
- user_id uuid not null FK users(id)
- refresh_token_hash text unique not null
- status text not null default `active`
- access_token_jti text nullable
- created_at timestamptz not null
- updated_at timestamptz not null
- expires_at timestamptz not null
- revoked_at timestamptz nullable
- last_used_at timestamptz nullable
- ip_hash text nullable
- user_agent text nullable

Constraints/indexes:

- `sessions.status` CHECK IN (`active`, `revoked`, `expired`).
- `sessions.refresh_token_hash` unique.
- `sessions.user_id` FK users(id).
- `sessions.revoked_at` required when status = `revoked`.
- index `sessions(user_id, status, created_at desc)`.
- index `sessions(refresh_token_hash)` unique.
- index `sessions(access_token_jti)` when not null.
- index `sessions(expires_at)`.

Rules:

- Store only refresh token hash.
- Never store raw refresh token.
- Rotate refresh token on refresh.
- Logout marks session `revoked`; no hard delete.
- Expired sessions cannot refresh.
- Blocked users cannot refresh or operate.

## audit_logs

Required events:

- user_created
- user_login
- user_logout
- session_refreshed
- auth_failed

Rules:

- Do not store raw initData.
- Do not store JWT or refresh token.
- Do not store BOT_TOKEN or secrets.
- Use `resource_type/resource_id`.
- Include `request_id`.

Builder must update `04_DATA/DATA_MODEL_MASTER.md`, `DATABASE_CONSTRAINTS.md` and `INDEXES.md` if implementation needs fields not listed here.

