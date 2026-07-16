# AUDIT_EVENTS.md

Eventos obligatorios:

- `admin_user_list_viewed`
- `admin_user_detail_viewed`
- `user_suspended`
- `user_reactivated`
- `user_blocked`
- `business_access_linked`
- `business_access_unlinked`
- `business_access_suspended`
- `business_access_reactivated`
- `business_access_revoked`
- `business_access_blocked`
- `surface_access_denied`

Audit metadata no debe incluir tokens, Authorization, refresh hashes, `storage_path`, `account_value`, datos bancarios completos ni datos sensibles sin masking.
