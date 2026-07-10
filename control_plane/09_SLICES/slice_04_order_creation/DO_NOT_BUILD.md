# DO_NOT_BUILD.md

Do not build:

- payment evidence upload
- business confirm payment
- delivery
- disputes

Global prohibitions:

- No invented states/enums.
- No escrow/protected-funds/guaranteed-delivery claims.
- No direct DB mutations outside services.
- No Frankenstein functions mixing permissions, queries, state transitions, audit and HTTP response.
- No READY_FOR_REAL_USE claim by builder.