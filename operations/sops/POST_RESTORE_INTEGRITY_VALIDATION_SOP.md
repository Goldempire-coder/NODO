# SOP: Post Restore Integrity Validation

SOP_ID: SOP-POST-RESTORE-INTEGRITY-001
Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Proposito

Validar que un restore no dejo NODO con datos monetarios, permisos, audit, storage o estados inconsistentes.

## Alcance

- Postgres.
- Storage privado.
- Redis readiness.
- Backend health/readiness/version.

## Cuando usar

- Despues de cualquier restore DB.
- Despues de restore storage.
- Despues de restore combinado DB+storage.

## Cuando no usar

- Como sustituto de restore.
- Contra produccion sin aprobacion.

## Permisos requeridos

- Owner approval para entorno real.
- Acceso read-only a DB restaurada.
- Acceso storage limitado para validar existencia de objetos.

## Comandos reales existentes

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\post_restore_schema_<timestamp>.json
```

COMMAND NOT AVAILABLE para validacion completa de integridad negocio/storage. Debe construirse en 31C/31E.

## Checks minimos futuros

- `credit_wallets` sin saldos negativos.
- `credits_ledger` exact-once por purchase/order.
- `credit_purchase_onchain_payments(chain_id, tx_hash, tx_log_index)` unico.
- `orders` con `order_state_events` coherentes.
- `payment_reports` asociados a orden propia.
- `business_access_links` activos consistentes con `users` y `businesses`.
- `staff_permissions` activos consistentes con `staff_profiles`.
- `audit_logs` presentes para mutaciones sensibles.
- `file_assets` apunta a objetos storage existentes.
- `notification_jobs` sin dedupe roto.
- `sessions` no reactivan usuarios blocked/restricted sin auth refresh valido.

## Criterio de exito

- Schema validation OK.
- Integrity checks OK.
- Storage references OK.
- Health/ready/version OK.
- No secrets/private paths in evidence.

## Criterio de aborto

- Ledger/wallet mismatch.
- Audit trail faltante.
- DB/storage mismatch.
- Restore reabre access links o staff revocados.
- Cualquier secreto en output.

## Evidencia requerida

- JSON de schema validation.
- JSON de integrity checks.
- Conteos anonimizados.
- Lista de failures sin datos privados.

## Estado

BLOCKED hasta tooling 31C/31E.
