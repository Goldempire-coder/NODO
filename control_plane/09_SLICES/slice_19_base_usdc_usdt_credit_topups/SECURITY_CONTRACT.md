# SECURITY_CONTRACT.md

## Auth/RBAC

- Business endpoints requieren JWT valido, `business_owner`, negocio aprobado y `business_access_links.status = active`.
- Admin review requiere admin/super_admin.
- Support solo lectura/enmascarado.

## Secrets

Secretos backend:

- `BASE_RPC_URL`
- `BASE_RPC_API_KEY` si proveedor lo requiere

No secretos:

- `NODO_CREDIT_RECEIVING_WALLET_BASE` es direccion publica, pero sigue siendo config operacional y no debe aparecer en logs innecesarios.

Prohibido guardar o usar:

- private key
- seed phrase
- signing key
- wallet mnemonic

## Data exposure

- No `storage_path`.
- No `account_value`.
- No RPC keys.
- No Authorization.
- No raw provider responses.
- Tx hash completo solo en detalle autorizado si es necesario para soporte/admin; listas/audit/logs usan masked/truncated.

## Rate limit

Rate limit obligatorio para:

- create base payment
- tx hash submit
- purchase status polling
- admin on-chain review
- watcher trigger/dry-run si se expone

## No authority bot

Bot privado/admin solo notifica. No acredita, no rechaza y no decide.
