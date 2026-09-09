# A-10_USERS_REMITTERS.md

SCREEN_ID: A-10_USERS_REMITTERS
actor: admin/support
slice: slice_20A_admin_users_business_control
surface: Admin Web Desktop
status: CONTRACT_READY

purpose:
Centro de operaciones para buscar clientes/usuarios/negocios por identidad operacional, ver detalle seguro y controlar estado de usuario/access links segun RBAC.

route:
/admin/users

entry points:
- Admin sidebar
- Admin dashboard
- Business detail access links

exit points:
- User detail split panel
- Business detail
- Access link detail/status action

data required:
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/{id}`
- `GET /api/v1/admin/users/{id}/access-links`
- `GET /api/v1/admin/businesses/{id}/access-links`

read strategy:
- Cursor pagination.
- Filters: phone, telegram_id, username, role, status.
- Loading skeleton.
- Empty state.
- Error/retry.
- Forbidden state.
- Masked data by default.

write strategy:
- Writes only through approved backend endpoints.
- No direct frontend state transition.
- Mutations require modal confirmation, reason and idempotency key.

Admin Web desktop rules:
- Use NODO design tokens and admin web components.
- Desktop-first layout with sidebar navigation and administrative top bar.
- Use dense but legible table, filters, search and split/detail panel.
- No Telegram Mini App shell, no Telegram bottom nav and no Telegram MainButton.

Primary actions:
- Suspend user: `POST /api/v1/admin/users/{id}/suspend`.
- Reactivate user: `POST /api/v1/admin/users/{id}/reactivate`.
- Block user: `POST /api/v1/admin/users/{id}/block`.
- View access links by user/business.
- Create/suspend/reactivate/revoke/block business access links only for admin/super_admin.

validation:
- reason required for mutations.
- Idempotency-Key required for mutations.
- support cannot mutate.
- admin cannot mutate admin/super_admin users.
- last active super_admin cannot be suspended/blocked.

permissions:
- admin: read + allowed mutations except protected admin/super_admin targets.
- super_admin: read + allowed mutations with last-super-admin protection.
- support: read-only, masked.
- remitter/business_owner: forbidden.

states:
- loading
- empty
- error
- offline
- forbidden
- success
- mutation_pending
- mutation_success
- mutation_error

audit events:
- admin_user_list_viewed
- admin_user_detail_viewed
- user_suspended
- user_reactivated
- user_blocked
- business_access_linked
- business_access_suspended
- business_access_reactivated
- business_access_revoked
- business_access_blocked

QA checklist:
- No PII leak.
- No tokens/session hashes/refresh hashes.
- No `storage_path`.
- No `account_value`.
- Support read-only.
- Reason/idempotency required.
- Blocked user denied from surfaces.
- Suspended/revoked/blocked business access link denies Mini App Negocio.
