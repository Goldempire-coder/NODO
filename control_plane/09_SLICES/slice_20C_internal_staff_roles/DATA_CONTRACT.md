# DATA_CONTRACT.md

## Tablas

### staff_profiles

- `id uuid primary key`
- `user_id uuid not null references users(id)`
- `staff_role text not null`
- `status text not null`
- `display_name text null`
- `created_by_super_admin_id uuid not null references users(id)`
- `activated_by_super_admin_id uuid null references users(id)`
- `suspended_by_super_admin_id uuid null references users(id)`
- `revoked_by_super_admin_id uuid null references users(id)`
- `activated_at timestamptz null`
- `suspended_at timestamptz null`
- `revoked_at timestamptz null`
- `reason text null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### staff_permissions

- `id uuid primary key`
- `staff_profile_id uuid not null references staff_profiles(id)`
- `permission text not null`
- `scope text not null`
- `scope_value text null`
- `status text not null`
- `granted_by_super_admin_id uuid not null references users(id)`
- `revoked_by_super_admin_id uuid null references users(id)`
- `revoked_at timestamptz null`
- `reason text not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

### staff_invites

- `id uuid primary key`
- `target_user_id uuid null references users(id)`
- `target_telegram_id bigint null`
- `target_username text null`
- `invite_code_hash text null`
- `staff_role text not null`
- `status text not null`
- `expires_at timestamptz not null`
- `created_by_super_admin_id uuid not null references users(id)`
- `accepted_by_user_id uuid null references users(id)`
- `accepted_at timestamptz null`
- `revoked_at timestamptz null`
- `expired_at timestamptz null`
- `reason text not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

## Read models

- `staff_activity` no es tabla MVP; se calcula desde `audit_logs`, `support_ticket_events` y eventos `staff_*`.

## Constraints

- `staff_profiles.staff_role` debe estar en enum canonico de staff.
- `staff_profiles.status` debe ser `active|suspended|revoked`.
- `staff_permissions.status` debe ser `active|revoked`.
- `staff_invites.status` debe ser `pending|accepted|expired|revoked`.
- Reason obligatorio para crear invitacion, cambiar permisos, suspender o revocar.
- Solo un `staff_profiles.status = active` por `user_id`.
- No hard delete.
- No se puede suspender/revocar/bloquear el ultimo `super_admin active` por efectos combinados de usuario/staff.

## Indexes

- `staff_profiles(user_id, status)`.
- `staff_profiles(staff_role, status, created_at desc)`.
- unique parcial `staff_profiles(user_id)` where status = `active`.
- `staff_permissions(staff_profile_id, status)`.
- unique parcial `staff_permissions(staff_profile_id, permission, scope, scope_value)` where status = `active`.
- `staff_invites(status, expires_at)`.
- `staff_invites(target_user_id, status)` parcial cuando target_user_id no sea null.
- `staff_invites(target_telegram_id, status)` parcial cuando target_telegram_id no sea null.
- `staff_invites(lower(target_username), status)` parcial cuando target_username no sea null.
