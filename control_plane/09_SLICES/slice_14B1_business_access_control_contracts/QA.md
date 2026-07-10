# QA.md

## Contract tests expected when build is approved

- Business Mini App calls `surface/session` before `businesses/me`.
- User with role `business_owner` but no active link is denied.
- Approved business with suspended link is denied operational access.
- Approved business with blocked link is denied.
- Pending/suspended/blocked business returns governed access state.
- Bot intake does not create active business or link.
- Admin link/unlink/suspend/reactivate/block requires reason and audit.
- Self-onboarding endpoints are not reachable from Mini App Negocio UI.
- `surface_access_denied` is audited where applicable.
