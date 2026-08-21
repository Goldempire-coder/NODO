# 52B API Contract

## Listado

`GET /api/v1/admin/credit-purchases`

- Auth y RBAC existentes.
- Filtros existentes: status y business_id.
- Default 20, maximo 50, `next_cursor` opaco.
- Respuesta: `AdminCreditPurchaseSummary[]`.
- No incluye ledger, proof metadata, direcciones, hashes completos ni payload raw
  del proveedor.

`AdminCreditPurchaseSummary` contiene solo:

- id, business_id, package_code, credits_amount, price_usd
- payment_method, status, verification_status, has_reported_tx
- created_at, updated_at

## Detalle bajo demanda

`GET /api/v1/admin/credit-purchases/{id}`

Respuesta aditiva:

```json
{
  "purchase": {},
  "onchain_evidence": {},
  "ledger": null,
  "reconciliation": {
    "state": "pending",
    "warning_codes": []
  }
}
```

- `onchain_evidence` usa hashes y direcciones enmascarados.
- Los campos de ubicacion del evento son `tx_block_number` y `tx_log_index`.
- `ledger` es el movimiento `purchase` relacionado por
  `related_credit_purchase_id`, o null.
- `reconciliation` es calculada por backend y nunca acredita ni corrige datos.
- `CREDITED_WITHOUT_LEDGER` indica inconsistencia operativa para revision.
- El endpoint mantiene `Cache-Control: private, no-store`.

## Rechazo Admin

`POST /api/v1/admin/credit-purchases/{id}/reject`

- Es la unica ruta oficial de rechazo.
- Requiere Admin/Super Admin, reason e Idempotency-Key segun contrato vigente.
- Acepta manual `pending_manual_review` y on-chain `under_review`.
- No acredita creditos.
- Support no puede ejecutar la accion.

No existe una ruta separada `onchain-reject` en 52B.
