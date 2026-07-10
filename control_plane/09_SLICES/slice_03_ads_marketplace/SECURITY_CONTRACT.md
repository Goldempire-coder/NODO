# SECURITY_CONTRACT.md

Security requirements:

- Only authenticated remitters can search/view marketplace.
- Only approved business owners can create/update/pause/archive own ads.
- Owner-only ad mutations.
- Business must be `verification_status = approved`.
- Business/ad must not be suspended/blocked/high risk for publication.
- Support/admin do not mutate ads in this slice unless a future admin endpoint is explicitly approved.
- Rate limits on search, detail, create, update, pause and archive.
- Redis-backed rate limits in runtime normal; in-memory only in test.
- Idempotency required on create, update, pause and archive.
- Audit log for all sensitive state/data changes.
- Credits hold/release must be transactional with wallet and ledger.
- Marketplace responses must not expose private business payment account values, storage paths, documents, tokens or Telegram IDs.

Mandatory controls:

- Backend RBAC, not frontend-only hiding.
- Ownership checks for business/ad resources.
- State machine for ad transitions.
- Credit service for wallet/ledger mutation.
- Safe errors using `ERROR_CONTRACT.md`.
- Secrets never in frontend bundle or repo.

If any control is missing, stop with `BLOCKED_BY_SECURITY_GAP`.
