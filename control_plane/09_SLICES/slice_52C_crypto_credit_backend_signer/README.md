# slice_52C_crypto_credit_backend_signer

Estado: `CONTRACT_RECONCILED_READY_FOR_IMPLEMENTATION`

## Objetivo

Definir la frontera segura para que NODO emita autorizaciones firmadas de
compras crypto de creditos publicitarios sin convertir el signer en una maquina
de firmar payloads controlados por frontend.

52C no despliega contrato, no configura wallets reales, no mueve fondos y no
activa dinero real. Reconcila el contrato para una implementacion futura.

## Regla Maestra

```txt
Frontend = expresa intencion
Backend = decide verdad comercial
Signer = certifica esa verdad
Contrato = verifica certificacion
Backend = acredita despues de verificar blockchain
```

## Decision Owner

NODO puede usar un `authorizedSigner` operacional para firmar autorizaciones
EIP-712 de compras crypto, con estas restricciones:

- la private key de treasury no vive en backend;
- la private key de owner/multisig no vive en backend;
- la private key del signer no vive en frontend, repo, logs, auditoria,
  screenshots ni respuestas API;
- produccion no debe usar una private key plana en Railway/env como custodia
  final;
- staging/testnet puede usar signer temporal con fondos pequenos, rotacion y
  evidencia, siempre marcado como no produccion;
- el signer solo firma snapshots creados por backend desde catalogo oficial;
- no existe endpoint publico o admin para firmar typed data arbitraria.

## Alcance 52C1

- Crear compra contractual segura desde backend.
- Recibir solo `package_code` y `payer_wallet_address`.
- Rechazar campos comerciales enviados por frontend: amount, token, chain,
  treasury, contract address, contract version, expiry y purchase ref.
- Derivar negocio desde sesion.
- Resolver paquete, creditos, precio, token, chain, contrato, version y
  expiracion desde configuracion backend.
- Generar `purchase_ref` bytes32 aleatorio, no enumerable.
- Guardar snapshot durable.
- Emitir autorizacion firmada solo si la configuracion y el negocio son validos.
- No acreditar creditos.

## Dependencia De Firma

52C1 usa `eth-account==0.13.7` y fija tambien `eth-abi==5.2.0` en
`apps/api/requirements.txt`.

Motivo:

- implementa encoding EIP-712 compatible con Ethereum;
- produce firma secp256k1 recuperable por OpenZeppelin `ECDSA.recover`;
- evita criptografia propia;
- publica wheel Python y usa licencia MIT.

`eth-abi` se fija de forma directa porque el rango transitivo de `eth-account`
tambien admite prereleases. El pin evita que una instalacion limpia seleccione
automaticamente `eth-abi 6.0.0b1` para una ruta critica de firma.

`eth-account` no instala comandos de consola propios. Su grafo incluye `ckzg`,
que distribuye una extension nativa para funciones KZG aunque 52C1 no la invoca.
Se acepta como dependencia transitiva del paquete oficial elegido, pero debe
permanecer en el inventario/SBOM y en el escaneo de dependencias antes de un
candidato de produccion.

## Limite Operativo 52C1

El runtime aplica los gates antiabuso 52C antes de firmar:

- 5 creaciones/reemisiones por usuario y por negocio cada 10 minutos;
- 20 por IP hasheada cada 10 minutos;
- maximo 3 compras contractuales no terminales por negocio;
- Redis/limitador compartido obligatorio en staging/produccion y fallo cerrado
  si no esta disponible.

El conteo durable PostgreSQL serializa por negocio y usa los estados
`pending_payment`, `pending_onchain_confirmation`, `detected` y `under_review`.
Memory conserva la misma semantica bajo lock. Un replay idempotente se resuelve
antes del conteo y no consume otro cupo pendiente. Alcanzar el cupo o perder el
limitador compartido no crea compra, no firma, no crea ledger y no cambia saldo.

La dependencia no cambia la regla de custodia: la clave plana solo se admite
para signer temporal local/testnet. Produccion requiere signer externo/KMS/HSM
o una decision Owner separada.

## Compatibilidad Legacy Del Endpoint

`POST /api/v1/business/credits/base-payment` conserva temporalmente el body
legacy solo cuando no existe ninguna configuracion contractual 52C y el flag
legacy esta habilitado. En cuanto existe contrato, version o signer 52C, el
modo contractual es la unica autoridad y un body legacy devuelve
`422 VALIDATION_ERROR`. Los dos modos no pueden operar a la vez.

El cliente legacy debe migrarse en un slice frontend separado antes de habilitar
52C en ese ambiente.

El resultado de la migracion es:

- `base_usdc_contract` como unico flujo normal de la App Negocio;
- sin wallet directa ni campo para pegar `tx_hash` en la UI normal;
- `base_usdc_onchain` solo local/staging o fallback manual/Admin;
- una transferencia directa nunca auto-acredita con trafico real controlado;
- el endpoint de `tx-hash` rechaza compras contractuales y solo conserva
  compatibilidad legacy gobernada.

## Rollback De 0057

El `down` de 0057 es seguro antes de crear compras `base_usdc_contract`. Si ya
existen compras contractuales, falla antes de modificar constraints o columnas
con un mensaje explicito. No borra ni convierte registros financieros. Un
rollback posterior a activacion requiere una migracion de transicion aprobada.

## Alcance 52C2

- Frontend de compra contractual.
- Reanudacion bajo demanda desde detalle propio, sin polling ni reemision por
  efecto lateral.
- Watcher/verificador por evento del contrato.
- Verificacion de receipt, evento NODO, Transfer ERC20, token, treasury, payer,
  amount, purchase_ref, chain, contrato, version y confirmaciones.
- Acreditacion exact-once mediante transaccion PostgreSQL existente.
- Limites por usuario, negocio, IP y maximo durable de compras pendientes.

## 52C2D-S0 Autoridad De Red

La compra contractual usa un perfil cerrado elegido solo por backend mediante
`NODO_CREDIT_PAYMENT_NETWORK`:

- `base_sepolia`: chain `84532`, USDC oficial de testnet y `is_testnet = true`;
- `base_mainnet`: chain `8453`, USDC oficial de Base y `is_testnet = false`.

El perfil fija conjuntamente red, chain y token. Firma EIP-712, handoff,
challenge, Memory y PostgreSQL reciben el mismo snapshot. Configuracion ausente,
desconocida o cambiada durante un handoff falla cerrado. El frontend de este
slice solo acepta `base_sepolia`; no ofrece selector y no puede activar mainnet.
Crear el handoff o la autorizacion sigue sin hacer `approve`, `pay`, watcher,
ledger, acreditacion ni movimiento de fondos.

La migracion 0058 reemplaza solo la restriccion de forma contractual de 0057:
conserva el perfil Base mainnet y agrega Base Sepolia como segunda tupla
canonica. Rechaza mezclas de chain, network y token, asi como contrato o version
faltantes. Su rollback falla antes de modificar constraints cuando existen
compras `base_sepolia`; no borra ni convierte datos financieros.

## Fuera De Alcance

- Cambiar contrato Solidity 52A.
- Deploy testnet/mainnet.
- Wallet oficial o fondos reales.
- Migracion aplicada en staging/produccion.
- Referrals, ordenes, anuncios, soporte, disputas o pagos P2P.
- Binance Pay, BSC, USDT BSC o tokens sin fuente oficial.

## Riesgo Principal

Si el backend firma datos que vienen del frontend sin recalcularlos desde
catalogo/configuracion oficial, el contrato funcionara correctamente pero NODO
habra autorizado una compra falsa. Por eso 52C trata al signer como frontera de
seguridad critica.

## 52C2C-S1 Telegram A MetaMask

La sesion Telegram no se transporta al navegador de MetaMask. La App Negocio
crea un handoff opaco de cinco minutos, protegido por owner y PIN, y abre
`/business/credit-payment` con el token solo en fragmento. La ruta elimina ese
fragmento antes de llamar API, conecta EIP-1193 en Base y usa `personal_sign`
para probar control de la wallet. 52C2D-S0 usa Base Sepolia `84532` y rechaza
un challenge mainnet o un perfil desconocido antes de solicitar la firma.

Backend guarda solo hash del token en Memory local o Redis compartido,
revalida acceso y PIN al reclamar, y usa idempotencia interna para preparar una
sola compra contractual. Telegram recupera con un `handoff_id` no sensible y
accion manual `Actualizar`. No hay polling, pago, approval, watcher, ledger,
acreditacion ni fondos en este slice.

## 52C2E-S0 Watcher Contractual

El watcher de creditos mantiene el flujo legacy por `tx_hash`, pero ahora
tambien puede revisar compras `base_usdc_contract` pendientes. No busca compras
sin snapshot completo y usa una busqueda agrupada por `purchase_ref` con
lookback acotado por
`ONCHAIN_CREDIT_CONTRACT_WATCHER_LOOKBACK_BLOCKS`.

Para una compra contractual, el watcher solo acepta evidencia si coinciden:

- evento `NodoCreditPaymentReceived` desde el contrato configurado;
- `purchase_ref`, payer, token, treasury, amount, chain, version y expiracion;
- receipt exitoso;
- `Transfer` ERC20 desde payer hacia treasury por el monto exacto;
- confirmaciones minimas.

Detectar o firmar no acredita por si solo. La acreditacion ocurre solamente al
pasar esa verificacion y reutiliza la transaccion PostgreSQL exact-once
existente. Un replay del worker no duplica ledger ni saldo. Si hay evidencia
Base Sepolia, 0059 permite almacenarla de forma canonica y su rollback falla de
forma controlada antes de cambiar constraints.

Este slice no agrega boton `pay`, `approve`, dependencia wallet, contrato
deployado, signer productivo, testnet real ni fondos.
