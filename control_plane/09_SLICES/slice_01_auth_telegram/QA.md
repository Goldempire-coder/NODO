# QA.md

Required QA:

- valid initData
- invalid hash
- expired initData
- new user
- existing user
- suspended user
- refresh/logout
- no bot token in bundle

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.