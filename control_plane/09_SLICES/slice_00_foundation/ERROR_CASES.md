# ERROR_CASES.md

Expected errors:

- ENV_MISSING
- DATABASE_UNAVAILABLE
- REDIS_UNAVAILABLE
- MIGRATION_FAILED

Rules:

- Use 06_API_CONTRACTS/ERROR_CONTRACT.md.
- Do not expose stack traces, SQL, secrets, tokens or private storage keys.
- Permission errors must not leak private resource existence.
- UI must map every expected error to a safe user state.