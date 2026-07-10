# SECURITY_CONTRACT.md

Security requirements:

Rate limits, security headers, secret scanning, RBAC tests, storage privacy, webhook signature tests, backup encryption.

Mandatory controls:

- Backend RBAC, not frontend-only hiding.
- Ownership checks for user/business/order resources.
- Rate limits on sensitive or high-traffic endpoints.
- Secrets never in frontend bundle or repo.
- Audit log for sensitive state/data changes.

If any control is missing, stop with BLOCKED_BY_SECURITY_GAP.