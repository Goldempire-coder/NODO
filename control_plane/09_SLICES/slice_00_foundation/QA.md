# QA.md

Required QA:

- frontend build
- backend tests
- migration up/down
- health/ready checks
- env validation
- Redis/DB connectivity

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.