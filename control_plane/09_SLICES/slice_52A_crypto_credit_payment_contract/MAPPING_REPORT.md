# 52A Mapping Report

> Documento historico de mapeo. No es autoridad normativa despues de 52C-S0.
> Para comportamiento futuro usar `CREDITS_API.md`, `API_CONTRACT.md` de 52A y
> `API_CONTRACT.md` de 52C. Las descripciones de wallet directa y `tx_hash`
> reflejan el flujo legacy observado, no el flujo normal aprobado.

Estado: `SIGNED_AUTH_CONTRACT_DRAFT_READY_FOR_OWNER_REVIEW`

## Alcance De La Evidencia

Este mapeo usa contratos del control plane y fuentes oficiales publicas. No se
leyo ni modifico runtime por restriccion de alcance. Por tanto, la descripcion
del flujo actual es contractual; su implementacion runtime queda
`NOT_VERIFIED` en 52A.

## Flujo Actual Contractual

1. `POST /api/v1/business/credits/base-payment` crea una compra
   `base_usdc_onchain` en `pending_payment`.
2. El backend fija Base 8453, USDC Base, monto, wallet destino y expiracion.
3. El negocio transfiere USDC a la wallet y puede enviar el `tx_hash`.
4. El watcher tambien puede detectar un `Transfer` hacia esa wallet.
5. El verifier valida receipt, chain, token, destino, monto, confirmaciones y
   unicidad `(chain_id, tx_hash, tx_log_index)`.
6. Wallet de creditos y ledger se actualizan exactamente una vez en PostgreSQL.

La unicidad evita doble credito, pero el `Transfer` no contiene la compra. Un
hash publico valido puede ser presentado por otro negocio antes que el pagador.

## Decision Recomendada

Implementar primero Base USDC mediante `NODOCreditPaymentVaultSigned`, sujeto a
Owner approval. Base 8453 y la direccion USDC Base estan documentadas por
fuentes oficiales. BSC no se selecciona todavia: la fuente oficial de Tether
revisada no publica USDt BSC y Circle no lista BSC para USDC.

## Flujo Propuesto

1. Frontend conecta wallet y envia `payer_wallet_address` al backend.
2. Backend crea compra y `purchase_ref` bytes32 aleatorio single-use.
3. Backend firma una autorizacion EIP-712 con payer, monto, chain, contrato,
   version y expiracion.
4. Backend devuelve snapshot de pago y `authorization_signature`.
5. Wallet externa aprueba el token y llama `pay(authorization, signature)`.
6. El vault valida firma, payer, monto, chain, contrato, version, expiracion y
   ref single-use.
7. El vault transfiere directo a treasury y emite el evento.
8. El watcher consume logs por rango de bloques del contrato allowlisted.
9. El verifier cruza evento, log ERC20 y snapshot durable.
10. PostgreSQL acredita wallet y ledger exact-once.

Wallet directa y pegar hash quedan como fallback manual. Nunca producen credito
automatico si falta el evento oficial ligado al `purchase_ref`.

## API Y Datos Propuestos

- `credit_purchases.onchain_purchase_ref`
- `credit_purchases.onchain_payer_address`
- `credit_purchases.payment_contract_address`
- `credit_purchases.payment_contract_version`
- `credit_purchases.payment_authorization_expires_at`
- `credit_purchase_onchain_payments.payment_contract_address`
- `credit_purchase_onchain_payments.purchase_ref`
- `credit_purchase_onchain_payments.payer_address`
- identidad durable del evento: `chain_id + tx_hash + tx_log_index`
- snapshot durable de chain, token, treasury, monto, expiracion y confirmaciones

Indices, tipos SQL, constraints y migracion requieren un slice posterior con
inspeccion runtime. No se proponen indices sin query y `EXPLAIN` representativo.

## Retiro Owner

- Los pagos aceptados van directamente a `treasury` immutable.
- Backend, frontend y watcher no guardan llaves ni firman transacciones.
- Owner controla treasury fuera de NODO y puede enviar fondos a un exchange.
- Recomendacion: treasury y owner del vault separados; owner mediante multisig.
- Cambio de treasury/token requiere contrato nuevo, release auditado, pausa del
  anterior y allowlist backend actualizada.

## Alertas Futuras

Telegram Admin debe alertar de forma idempotente y sin secretos por:

- configuracion de contrato/token/treasury ausente o invalida;
- contrato pausado/despausado;
- sweep;
- evento rechazado por chain/token/treasury/ref;
- pago parcial, vencido o duplicado;
- watcher/RPC degradado;
- acreditacion exact-once completada.

La alerta es informativa: nunca acredita, pausa ni mueve fondos.

## Decisiones Owner Pendientes

1. Aprobar Base USDC como primer despliegue o esperar fuente oficial BSC.
2. Para BSC, elegir USDt o USDC solo despues de fuente oficial del emisor.
3. Elegir Foundry o Hardhat.
4. Definir treasury temporal de testnet/staging, sin publicarla en docs.
5. Definir treasury oficial y si sera multisig.
6. Definir owner del vault; recomendacion: multisig separado de treasury.
7. Exigir o no auditoria externa antes de fondos reales.
8. Confirmar que wallet directa + tx hash queda solo manual/under_review.

## Fuentes Oficiales Revisadas

- Base network: https://docs.base.org/base-chain/quickstart/connecting-to-base
- Circle USDC addresses: https://developers.circle.com/stablecoins/usdc-contract-addresses
- BNB Smart Chain RPC/chain id: https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/
- BNB wallet configuration: https://docs.bnbchain.org/bnb-smart-chain/developers/wallet-configuration/
- Tether supported protocols: https://tether.to/en/supported-protocols/
- OpenZeppelin ERC20/SafeERC20: https://docs.openzeppelin.com/contracts/5.x/api/token/erc20
- OpenZeppelin security utils: https://docs.openzeppelin.com/contracts/5.x/api/utils
- OpenZeppelin access/Ownable2Step: https://docs.openzeppelin.com/contracts/5.x/api/access

No se adopto ninguna direccion BSC obtenida de exploradores, blogs, tutoriales
o resultados de busqueda.
