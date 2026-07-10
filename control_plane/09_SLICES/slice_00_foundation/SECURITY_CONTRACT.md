# SECURITY_CONTRACT.md

Security requirements:

Secrets outside repo, env validation, CORS, security headers, base auth middleware stub, structured logging without secrets.

Mandatory controls:

- Backend RBAC, not frontend-only hiding.
- Ownership checks for user/business/order resources.
- Rate limits on sensitive or high-traffic endpoints.
- Secrets never in frontend bundle or repo.
- Audit log for sensitive state/data changes.

If any control is missing, stop with BLOCKED_BY_SECURITY_GAP.