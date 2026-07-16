# SOP: Credit Topup Investigation

SOP_ID: SOP-CREDITS-001
Estado de validacion: NOT VALIDATED

## Proposito

Investigar creditos que no aparecen, aparecen duplicados o quedan pendientes.

## Datos necesarios

- `credit_purchase_id`
- `business_id`
- `tx_hash_masked` o hash completo solo en sistema autorizado
- `request_id`
- estado de `credit_purchases`
- evento en `credits_ledger`

## Procedimiento

1. Buscar compra en Admin Web `/admin/credit-purchases/{id}`.
2. Revisar status: `pending_payment`, `pending_onchain_confirmation`, `detected`, `credited`, `under_review`, `rejected`, `verification_failed`.
3. Si hay tx hash, revisar si watcher lo proceso.
4. Si hay duplicado, abrir SEV-1 y usar `DUPLICATE_CREDITS_RUNBOOK.md`.
5. No acreditar manualmente sin audit/reason.

## Validacion

- Una compra acreditada debe tener `credits_ledger.type = purchase`.
- Debe estar ligada por `related_credit_purchase_id`.
- No debe existir doble ledger para la misma compra.
