# QA.md

Required QA for slice 04:

- create order success.
- create order with inactive ad fails.
- create order with expired ad fails and/or materializes expiration.
- create order with `in_order` ad fails.
- create order with business not `approved` fails.
- amount below/above ad range fails.
- amount above business limit fails.
- idempotent double click returns same order or canonical safe idempotency error.
- create order does not consume credits.
- create order moves ad to `in_order`.
- create order stores immutable snapshot.
- detail/list do not reveal full payment instructions.
- detail/list do not reveal `account_value`.
- cancel `waiting_payment` releases ad/credits.
- cancel after payment reported is prohibited.
- extend payment deadline once only.
- foreign order access is forbidden.
- safe errors: no stack traces, SQL, tokens, secrets, account values or instructions.
- audit events and `order_state_events` are written for state changes.
- frontend build.
- runners 00, 01, 02, 03 and 04.
- backend pytest accumulated.
- ruff.
- compileall.
- frontend source/build secret and private data scan.

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.
