# DO_NOT_BUILD.md

Do not build:

- admin-only Telegram whitelist as sole control
- direct DB mutations
- unaudited exports
- slice 10 jobs, auto-complete or notification workers
- ratings/completion flows outside admin dispute resolution
- rebuilding slice 08 credit payment/manual adjustment screens as new owners
- escrow, protected-funds or guaranteed-delivery claims
- automatic Zelle processing
- sensitive export unless explicitly implemented as blocked and safe

Global prohibitions:

- No invented states/enums.
- No escrow/protected-funds/guaranteed-delivery claims.
- No direct DB mutations outside services.
- No Frankenstein functions mixing permissions, queries, state transitions, audit and HTTP response.
- No READY_FOR_REAL_USE claim by builder.
