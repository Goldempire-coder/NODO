# DO_NOT_BUILD.md

Do not build:

- customer remittance funds
- escrow
- automatic Zelle processing
- changes to ads/orders credit consumption already built
- jobs masivos
- admin completo fuera de creditos
- slice 09
- duplicate screens for non-canonical names

Global prohibitions:

- No invented states/enums.
- No escrow/protected-funds/guaranteed-delivery claims.
- No direct DB mutations outside services.
- No Frankenstein functions mixing permissions, queries, state transitions, audit and HTTP response.
- No secrets Stripe in frontend/repo/logs/responses.
- No `storage_path` in API/frontend/logs/audit.
- No credit from Stripe redirect.
- No manual payment auto-approval.
- No READY_FOR_REAL_USE claim by builder.
