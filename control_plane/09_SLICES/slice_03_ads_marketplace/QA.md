# QA.md

Required QA:

- cost 1/2/3 credits by range
- >2000 blocked/manual
- 7-day expiry
- click does not consume
- search filters
- owner isolation

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.