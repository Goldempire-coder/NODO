# ACCEPTANCE_CRITERIA.md

Para pasar a owner review:

- Base USDC purchase creado con idempotencia.
- Verifier valida chain/token/destination/amount/confirmations.
- Watcher reentrante con lock multi-worker.
- Tx hash submit seguro.
- Ledger/wallet exact-once.
- Referral qualification supports `approved` legacy purchases and `credited` Base USDC purchases only when an exact-once ledger purchase exists.
- On-chain minor unit fields use `numeric(78,0)`.
- EVM values are normalized consistently before persistence/comparison.
- Admin review limitado a `under_review`.
- Secrets scan limpio.
- No frontend/backend expone private key, seed phrase, RPC key, `storage_path` o `account_value`.
- Tests de wrong chain/token/wallet/duplicate/partial/expired pasan.
- No se declara READY_FOR_REAL_USE.
