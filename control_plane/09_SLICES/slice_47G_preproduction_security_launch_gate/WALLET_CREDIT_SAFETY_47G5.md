# Slice 47G5 - Wallet/Secrets + Credit Assignment Safety

Estado: IMPLEMENTED_LOCAL_READY_FOR_VALIDATOR_REVIEW

## Autoridad y limites

- Wallet receptora: `NODO_CREDIT_RECEIVING_WALLET_BASE`, solo env backend.
- Red acreditable: Base mainnet, chain `8453`.
- Token acreditable: USDC nativo contratado, 6 decimales.
- El cliente elige paquete y envia tx hash. No envia wallet, chain, token, monto
  esperado, confirmaciones ni credits como autoridad.
- NODO no firma transacciones, no mueve fondos y no almacena material de firma
  de treasury/owner.
- 52C agrega un signer operacional separado para autorizar compras por contrato.
  Ese signer solo firma snapshots creados por backend, no mueve fondos y no debe
  estar en frontend, repo, logs, audit o respuestas API.

La direccion receptora es publica porque el negocio debe verla para pagar. Eso
no convierte su cambio en una operacion ordinaria: el destino se controla fuera
de la UI/API mediante configuracion backend auditada por el proceso de release.

## Defensa de acreditacion

Antes de acreditar, el backend revalida el resultado del proveedor contra el
snapshot durable de la compra. Deben coincidir tx hash, chain, contrato del
token, destino, monto minimo, confirmaciones y log index. Un proveedor caido o
indeterminado falla cerrado. Una compra vencida queda `under_review` y no recibe
creditos automaticamente.

PostgreSQL vuelve a comprobar estado, invariantes y expiracion bajo lock de fila
usando `database_now`. El ledger y la wallet se actualizan en la misma
transaccion. El unique `chain_id + tx_hash + tx_log_index` y el ledger por compra
impiden doble acreditacion. Memory conserva paridad mediante lock local.

## Auditoria segura

Eventos relevantes:

- `onchain_credit_purchase_created`;
- `onchain_tx_hash_submitted`;
- `onchain_payment_verification_failed`;
- `onchain_credit_purchase_under_review`;
- `onchain_credit_purchase_credited`;
- `credits_added`;
- `onchain_receiving_wallet_configuration_invalid`.

Audit registra solo codigo allowlist, estado, source, ledger id, monto de
creditos y tx hash enmascarado. No registra wallet privada, raw RPC response,
RPC URL/key, private key, seed phrase, mnemonic ni signer key.

## Smoke futuro de staging

No ejecutar sin autorizacion Owner para staging mutante.

1. Registrar build/SHA y confirmar que no es produccion.
2. Crear wallet temporal dedicada; NODO recibe solo su direccion publica.
3. Registrar actor, aprobacion y fingerprints enmascarados anterior/nuevo.
4. Configurar la direccion en backend y reiniciar solo staging.
5. Crear una compra Starter y enviar un monto pequeno exacto de USDC en Base.
6. Capturar antes/despues: purchase, saldo de creditos, un ledger `purchase`,
   tx/log usado y audit, todo enmascarado.
7. Repetir submit/watcher para demostrar que no aparece un segundo ledger.
8. Probar una tx de destino o monto incorrecto en fixture aislado, sin fondos
   adicionales, y confirmar cero credito.
9. Restaurar la configuracion anterior o retirar la wallet temporal segun la
   ventana aprobada; registrar evidencia de rollback.

No usar la wallet oficial final ni montos reales relevantes en este smoke.

## Alerta futura, no implementada

Un slice posterior puede encolar alerta Admin idempotente para configuracion
ausente/invalida, intentos repetidos con destino incorrecto, tx duplicada y
fallo prolongado del RPC. Debe incluir solo purchase id publico/interno,
fingerprint o tx hash enmascarado, codigo y estado; nunca datos de firma ni raw
provider response. Fallar al alertar no puede acreditar ni cambiar la compra.

## No incluido

No se configuro wallet oficial o temporal, no se tocaron staging/produccion, no
se implemento Telegram, no se movieron fondos y no se cambiaron pagos P2P,
ordenes, marketplace, holds, rating ni uploads.
