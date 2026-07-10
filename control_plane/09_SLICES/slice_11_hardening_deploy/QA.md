# QA.md

Required QA:

- 2,000 active orders simulation
- webhook duplicate tests
- backup/restore
- rollback drill
- smoke tests
- security tests
- monitoring alerts

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.