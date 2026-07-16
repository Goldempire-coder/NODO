# QA.md

## Backend/API

- crear compra Base USDC requiere Idempotency-Key.
- misma key + mismo payload devuelve misma compra.
- misma key + payload distinto falla.
- tx valida acredita una vez.
- tx duplicada no acredita doble.
- wrong chain falla.
- wrong token falla.
- wrong wallet falla.
- insufficient amount queda `under_review`.
- expired purchase no acredita automatico.
- pending confirmations no acredita.
- RPC unavailable devuelve error seguro.
- concurrent tx submit no duplica.
- watcher batch no duplica.
- ledger append-only.
- wallet no queda negativa.
- Base USDC purchase with `credited` status and exact-once ledger purchase qualifies referral.
- Base USDC purchase before `credited` does not qualify referral.
- Stripe/manual `approved` purchase remains referral-qualifying when exact-once ledger purchase exists.
- EVM values are normalized before compare; mixed-case tx/address inputs do not bypass duplicate/token/wallet checks.
- bot/admin privado no acredita.

## Seguridad

- no private key.
- no seed phrase.
- no RPC keys en frontend/respuestas/logs.
- no `storage_path`.
- no `account_value`.
- tx hash masked en listas/audit/logs.
- no claims de anonimato/evasion/escrow/fondos garantizados.

## UI

- B-05 muestra Base USDC como flujo principal.
- B-06 muestra estados on-chain y permite tx hash.
- B-07 muestra ledger seguro.
- USDT TRC20 manual no se mezcla con Base.
