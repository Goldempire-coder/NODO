# 52B Security Contract

## Datos permitidos

- IDs operativos de compra, negocio y ledger.
- Paquete, creditos, monto, moneda, metodo y estados.
- Saldos de creditos antes y despues.
- Red, token, bloque, log index y confirmaciones.
- Hashes, wallets y direcciones unicamente enmascarados.
- Comparaciones booleanas calculadas por backend.

## Datos prohibidos

- Private keys, seed phrases, mnemonics o signing keys.
- RPC keys, tokens, cookies, headers o session data.
- Raw provider responses.
- Telegram initData, telefonos completos o PII innecesaria.
- storage_path o signed URLs persistidas.
- Wallets, direcciones o hashes completos.

## Autoridad

- Backend calcula reconciliacion y warnings.
- Frontend solo presenta la proyeccion recibida.
- El detalle no acredita, rechaza, reintenta ni modifica wallet/ledger.
- Una compra acreditada sin ledger se reporta; no se repara automaticamente.
- Cualquier revelacion futura de valores completos requiere un slice separado con
  razon obligatoria, RBAC y auditoria.
