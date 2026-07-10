# DO_NOT_BUILD.md

Do not build:

- payment processing
- business verification
- credit purchase
- R-10_CONFIRM_RECEIVED
- R-11_RATING
- A-06_DISPUTES_LIST
- A-07_DISPUTE_DETAIL
- remitter confirm received
- order completion
- ratings
- auto-complete
- admin dispute resolution
- resolve_dispute
- POST /api/v1/admin/disputes/{id}/resolve
- credit release/consume/adjustment from dispute resolution
- jobs masivos

Global prohibitions:

- No invented states/enums.
- No escrow/protected-funds/guaranteed-delivery claims.
- No direct DB mutations outside services.
- No Frankenstein functions mixing permissions, queries, state transitions, audit and HTTP response.
- No READY_FOR_REAL_USE claim by builder.
