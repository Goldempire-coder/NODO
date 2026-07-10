# QA.md

Required QA:

- submit valid business
- reject incomplete data
- missing verification document rejects submit
- private verification document upload stores file metadata only
- verification document signed URL expires
- owner isolation
- admin approve/reject
- support cannot approve/reject
- reject without reason fails
- audit writes
- approved business can proceed to ads

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.
