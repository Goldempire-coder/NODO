# SECURITY_CONTRACT.md

Security requirements:

- Business owner can create and edit only own business.
- Guest cannot create, edit or view business verification resources.
- Admin/super_admin only can approve/reject.
- Support may view pending businesses according to RBAC, but cannot approve/reject or open full documents by default.
- Approve/reject require non-empty reason.
- Approve/reject only apply to `business.verification_status = pending`.
- Sensitive data masked by default.
- Verification documents are private uploads using `file_assets`; no public document URLs.

Mandatory controls:

- Backend RBAC, not frontend-only hiding.
- Ownership checks for business owner routes.
- State machine/service validates `pending`, `approved`, `rejected`, `suspended`, `blocked`.
- Rate limits on create/update/submit/upload/admin actions.
- Secrets never in frontend bundle or repo.
- Audit log for sensitive state/data changes.
- Signed URL max 5 minutes for document view.
- No storage path, signed URL, raw document, token or secret in audit logs.

If any control is missing, stop with `BLOCKED_BY_SECURITY_GAP`.
