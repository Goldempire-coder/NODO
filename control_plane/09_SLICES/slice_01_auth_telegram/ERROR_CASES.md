# ERROR_CASES.md

Expected errors:

- TELEGRAM_INIT_DATA_INVALID
- TELEGRAM_INIT_DATA_EXPIRED
- USER_SUSPENDED
- SESSION_EXPIRED
- RATE_LIMITED

Rules:

- Use 06_API_CONTRACTS/ERROR_CONTRACT.md.
- Do not expose stack traces, SQL, secrets, tokens or private storage keys.
- Permission errors must not leak private resource existence.
- UI must map every expected error to a safe user state.