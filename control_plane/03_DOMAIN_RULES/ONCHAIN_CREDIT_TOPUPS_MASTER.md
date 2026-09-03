# ONCHAIN_CREDIT_TOPUPS_MASTER.md

Contrato canonico para compra y acreditacion de creditos publicitarios con pagos on-chain.

## Alcance MVP slice 19

MVP usa solo:

- Network: Base mainnet.
- chain_id: `8453`.
- Token activo: USDC nativo en Base.
- Token contract USDC Base mainnet: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- Decimals: `6`.
- Destination wallet config: `NODO_CREDIT_RECEIVING_WALLET_BASE`.

Base Sepolia queda solo para tests y staging controlado. Base Sepolia no es red de acreditacion real.

USDT en Base queda fuera del MVP porque no hay contrato oficial Tether en Base verificado en la fuente canonica de Tether al momento de este contrato. Prohibido aceptar USDT por simbolo, nombre o token no verificado.

Referencias de token:

- Circle USDC contract addresses: `https://developers.circle.com/stablecoins/usdc-contract-addresses`
- Circle native USDC on Base announcement: `https://www.circle.com/blog/usdc-now-available-natively-on-base`

## Relacion con flujos previos

Flujo principal para fondos reales despues de 52A/52C:
`base_usdc_contract`, con contrato NODO, `purchase_ref` y autorizacion EIP-712
firmada. Este flujo reemplaza la confianza en un `tx_hash` publico como prueba
de intencion comercial.

Flujos legacy/fallback:

- `base_usdc_onchain`: wallet directa con verificacion on-chain; no debe usarse como flujo normal si el contrato esta activo.
- `stripe_checkout`: fallback permitido si sigue configurado.
- `zelle_manual_admin_approved`: fallback manual permitido solo con revision admin.
- `usdt_manual_admin_approved`: legacy manual TRC20. No se mezcla con Base. No puede acreditar automaticamente.

El frontend debe separar visualmente Base USDC de USDT TRC20 manual. No usar copy, estados ni endpoints de USDT TRC20 manual para Base.

## Principio de custodia

NODO recibe pagos por creditos publicitarios propios. Esto no convierte a NODO en custodio de fondos de remesa ni garante de operaciones entre remitente y negocio.

Prohibido:

- prometer escrow
- prometer fondos protegidos
- prometer recuperacion de fondos
- prometer anonimato o evasion
- decir que NODO recibe, retiene, transfiere o garantiza fondos de remesas

## Flujo Base USDC Directo A Wallet

1. Negocio aprobado entra a Mini App Negocio.
2. Selecciona paquete de creditos.
3. Backend crea `credit_purchases.status = pending_payment` con metodo `base_usdc_onchain`.
4. Backend devuelve:
   - purchase id
   - Base mainnet
   - chain_id `8453`
   - USDC contract oficial
   - amount exacto en unidades menores
   - destination wallet publica
   - expires_at
5. Negocio paga desde wallet externa.
6. Watcher detecta Transfer USDC hacia wallet destino o negocio pega tx hash.
7. Backend verifica on-chain.
8. Cuando cumple reglas, backend acredita creditos exactamente una vez.
9. Bot/admin privado solo notifica eventos; no decide ni acredita.

## Flujo Base USDC Por Contrato

1. Negocio aprobado entra a Mini App Negocio.
2. Selecciona paquete de creditos y conecta wallet.
3. Frontend envia solo `package_code` y `payer_wallet_address`.
4. Backend deriva negocio desde sesion.
5. Backend resuelve paquete, precio, token, chain, contrato, treasury,
   version, expiracion y `purchase_ref`.
6. Backend guarda snapshot durable.
7. Backend solicita firma del snapshot autorizado.
8. Contrato acepta `pay(authorization, signature)` solo si firma, payer, monto,
   chain, contrato, version, expiracion y ref coinciden.
9. Contrato mueve USDC del payer a treasury y emite evento NODO.
10. Backend verifica receipt, evento del contrato, Transfer ERC20,
    confirmaciones y snapshot.
11. Backend acredita creditos exactamente una vez.

## Verificacion on-chain obligatoria

Un pago solo puede acreditarse si todo es cierto:

- chain_id = `8453`.
- token contract = USDC Base oficial `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- decimals = `6`.
- destination wallet = `NODO_CREDIT_RECEIVING_WALLET_BASE`.
- amount en unidades menores es exactamente el esperado o mayor.
- transaction receipt existe y tiene status exitoso.
- Transfer log valido hacia destination wallet.
- min confirmations cumplidas.
- purchase no esta `credited`, `rejected`, `expired` ni `verification_failed`.
- tx/log no fue usado antes para acreditar creditos.
- ledger `purchase` para la compra no existe previamente.

## Monto

El monto esperado se calcula desde paquetes oficiales de creditos.

- Starter: 10.00 USDC, 5 creditos.
- Pro: 25.00 USDC, 15 creditos.
- Business: 75.00 USDC, 50 creditos.
- Enterprise: 250.00 USDC, 200 creditos.

Representacion:

- `price_usd` conserva valor humano decimal.
- `expected_amount_units` guarda unidades menores USDC con 6 decimales.
- Prohibido usar float.

## Estados canonicos de credit_purchase on-chain

Estados activos para `base_usdc_onchain`:

- `pending_payment`: purchase creada, esperando tx.
- `pending_onchain_confirmation`: tx detectada o submitida, esperando confirmaciones.
- `detected`: tx candidata detectada y guardada.
- `verified`: tx verificada, lista para acreditacion atomica.
- `credited`: wallet y ledger actualizados exactamente una vez.
- `under_review`: caso no acreditable automaticamente pero revisable por admin.
- `expired`: no se detecto pago valido antes de expiracion.
- `rejected`: admin rechazo caso revisable con reason.
- `verification_failed`: verificacion fallo por regla objetiva no revisable automaticamente.

Estados legacy:

- `pending_manual_review`, `paid`, `approved`, `failed` siguen para Stripe/manual previos, no son estados principales del flujo Base USDC.

## Transiciones

```txt
pending_payment -> detected
pending_payment -> pending_onchain_confirmation
pending_payment -> expired
detected -> pending_onchain_confirmation
pending_onchain_confirmation -> verified
verified -> credited
pending_payment -> under_review
detected -> under_review
pending_onchain_confirmation -> under_review
under_review -> rejected
pending_payment -> verification_failed
detected -> verification_failed
pending_onchain_confirmation -> verification_failed
```

Reglas:

- `credited` es terminal.
- `rejected` es terminal.
- `expired` es terminal salvo decision admin futura no incluida en MVP.
- `verification_failed` es terminal para errores objetivos: wrong chain, wrong token, wrong destination, duplicate tx.

## Casos borde

| Caso | Resultado MVP |
| --- | --- |
| Pago parcial | `under_review`; no acredita automatico. |
| Sobrepago | acredita solo creditos del paquete cuando el pago cumple minimo; no genera credito extra automatico ni reembolso automatico. |
| Pago vencido | `under_review`; no acredita automatico. |
| Red incorrecta | `verification_failed`; no acredita. |
| Token incorrecto | `verification_failed`; no acredita. |
| Wallet destino incorrecta | `verification_failed`; no acredita. |
| Tx duplicada | `verification_failed` o error `ONCHAIN_TX_ALREADY_USED`; no acredita. |
| Confirmaciones insuficientes | `pending_onchain_confirmation`; no acredita todavia. |
| RPC caido | mantener estado anterior y devolver `ONCHAIN_RPC_UNAVAILABLE` seguro. |
| Watcher detecta tarde | si purchase expiro, mover a `under_review`; no acredita automatico. |
| Varios pagos suman monto | `under_review`; no suma automatico en MVP. |

## Idempotencia y exact-once

- Crear purchase requiere `Idempotency-Key`.
- Submit tx hash requiere `Idempotency-Key`.
- Watcher debe ser reentrante.
- Unique canonico por `chain_id + tx_hash + tx_log_index`.
- Wallet y ledger se actualizan en una sola transaccion.
- Si existe ledger `purchase` por `related_credit_purchase_id`, no se vuelve a acreditar.
- Reintento del watcher con la misma tx devuelve mismo resultado o skip seguro.

## Watcher

Job canonico: `verify_base_usdc_credit_purchases`.

Config:

- `BASE_RPC_URL` secreto backend.
- `BASE_RPC_API_KEY` secreto backend cuando proveedor lo requiera.
- `NODO_CREDIT_RECEIVING_WALLET_BASE` direccion publica destino.
- `ONCHAIN_CREDIT_WATCHER_BATCH_SIZE` default 50.
- `ONCHAIN_CREDIT_WATCHER_TIMEOUT_SECONDS` default 10.
- `ONCHAIN_CREDIT_WATCHER_BACKOFF_SECONDS` default 30.
- `ONCHAIN_CREDIT_MIN_CONFIRMATIONS` default 6.
- `ONCHAIN_CREDIT_PURCHASE_TTL_MINUTES` default 30.

Reglas:

- usar lock multi-worker con TTL.
- no correr si faltan env vars criticas.
- no loguear RPC keys.
- no guardar respuestas RPC completas en audit.
- limitar llamadas por corrida.
- registrar `job_runs` con metadata segura.
- preferir batching por rango de bloques/logs antes que polling por compra cuando escale.

## Admin review

Admin/super_admin pueden revisar casos `under_review`.

En MVP admin puede:

- ver metadata on-chain enmascarada.
- rechazar con reason.
- devolver a pending para reintento solo si no hay ledger ni tx usada.

Admin no puede acreditar manualmente una tx on-chain sin que verifier marque `verified`. Si se requiere override manual, debe ser slice futuro con doble aprobacion.

Support es read-only y enmascarado.

## Audit events

- onchain_credit_purchase_created
- onchain_tx_hash_submitted
- onchain_payment_detected
- onchain_payment_confirmations_pending
- onchain_payment_verified
- onchain_credit_purchase_credited
- onchain_payment_under_review
- onchain_payment_rejected
- onchain_payment_verification_failed
- onchain_receiving_wallet_configuration_invalid
- onchain_tx_duplicate_detected
- onchain_watcher_run_started
- onchain_watcher_run_finished
- onchain_watcher_run_failed
- credits_added

## Prohibido

- aceptar tokens por simbolo/nombre solamente.
- aceptar USDT Base en MVP.
- aceptar USDT TRC20 como Base.
- acreditar por screenshot o texto libre.
- exponer private key, seed phrase, RPC keys o raw provider responses.
- guardar private key o seed phrase en backend, frontend, Railway, GitHub, Cursor, logs o evidencia.
- exponer `storage_path` o `account_value`.
- crear creditos sin ledger.
- mutar wallet directo fuera del servicio de creditos.

## Cambio de wallet receptora

`NODO_CREDIT_RECEIVING_WALLET_BASE` solo cambia mediante configuracion backend
controlada. No existe endpoint ni UI para modificarla. Cada cambio requiere
actor, aprobacion Owner, entorno, commit/build desplegado, fingerprint
enmascarado anterior/nuevo, timestamp, motivo, evidencia de smoke y plan de
rollback. La direccion es publica, pero el cambio de destino es una operacion
sensible y nunca silenciosa.

Private keys, seed phrases y mnemonics de treasury/owner no pertenecen a NODO.
El backend no firma transacciones ni mueve fondos.

52C autoriza un secreto operacional separado: `authorizedSigner` para firmar
solo autorizaciones EIP-712 de compra de creditos. Ese signer no es treasury, no
es owner, no mueve fondos y no debe vivir en frontend, repo, logs, auditoria ni
respuestas API. Produccion no debe usar una private key plana en Railway/env
como custodia final; staging/testnet puede usar signer temporal con fondos
pequenos y rotacion antes de produccion.
