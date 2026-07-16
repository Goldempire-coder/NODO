# AUDIT_EVENTS.md

Eventos obligatorios:

- onchain_credit_purchase_created
- onchain_tx_hash_submitted
- onchain_payment_detected
- onchain_payment_confirmations_pending
- onchain_payment_verified
- onchain_credit_purchase_credited
- onchain_payment_under_review
- onchain_payment_rejected
- onchain_payment_verification_failed
- onchain_tx_duplicate_detected
- onchain_watcher_run_started
- onchain_watcher_run_finished
- onchain_watcher_run_failed
- credits_added

Audit metadata debe ser segura:

- tx_hash masked salvo detalle admin autorizado.
- no RPC key.
- no raw provider response.
- no private key.
- no seed phrase.
- no `storage_path`.
- no `account_value`.
