# DO_NOT_BUILD.md

Do not build:

- business onboarding
- marketplace
- orders
- payments
- credits
- admin workflows

Global prohibitions:

- No invented states/enums.
- No escrow/protected-funds/guaranteed-delivery claims.
- No direct DB mutations outside services.
- No Frankenstein functions mixing permissions, queries, state transitions, audit and HTTP response.
- No READY_FOR_REAL_USE claim by builder.