# Slice 52A - Crypto Credit Payment Contract

## Autoridad Despues De 52C-S0

Este documento describe el contrato. La autoridad de la API business y la
migracion desde wallet directa vive en `CREDITS_API.md`, este slice
`API_CONTRACT.md` y el API contract de 52C.

Decision cerrada: `base_usdc_contract` es el unico flujo normal futuro. La App
Negocio no muestra wallet directa ni pide `tx_hash`. `base_usdc_onchain` queda
solo local/staging o fallback manual/Admin y nunca auto-acredita con trafico real
controlado.

Estado: LOCAL_CONTRACT_IMPLEMENTED_READY_FOR_OWNER_REVIEW

## Objetivo

Disenar el contrato crypto para recibir pagos de paquetes de creditos
publicitarios NODO sin depender de que un negocio pegue un hash publico ajeno.

El problema a cerrar es concreto:

```txt
Hoy una transferencia publica hacia la wallet NODO puede ser reclamada por el
primer negocio que pegue el hash si cumple red, token, destino y monto.
Exact-once evita duplicados, pero no prueba intencion de compra para ese negocio.
```

52A crea una intencion on-chain unica por compra. El backend acredita solo si
la transaccion contiene un evento oficial del contrato NODO con el `purchase_ref`
durable de esa compra.

Decision de seguridad: el diseno oficial del slice es **autorizacion firmada
V2**. El contrato no acepta un `purchase_ref` y un monto elegidos libremente por
quien llama. El backend firma los datos exactos de la compra y el contrato solo
acepta si esa firma coincide.

## Implementacion Local 52A1

Se agrego un paquete aislado en `apps/contracts` con:

- `NODOCreditPaymentVaultSigned`;
- mocks ERC20 para pruebas locales;
- Hardhat 3, viem y OpenZeppelin versionados en `pnpm-lock.yaml`;
- pruebas locales de firma, replay, monto alterado, payer, expiracion, pausa,
  rotacion de signer, sweep, ownership de dos pasos y rechazo de pago nativo.

Alcance: contrato local y pruebas. No hay deploy, backend runtime, frontend,
watcher, wallet real, staging, produccion ni fondos reales.

## Decision Recomendada

MVP recomendado:

- Mantener Base USDC como primera red automatica.
- Reemplazar el cobro directo a wallet por un contrato EVM
  `NODOCreditPaymentVaultSigned`.
- El contrato no decide creditos, no calcula paquetes y no toca la base de
  datos.
- El contrato transfiere el token permitido directamente a la tesoreria NODO y
  emite un evento con `purchase_ref`.
- El backend sigue siendo la autoridad de paquetes, vencimiento, credito,
  ledger, negocio y auditoria.

BNB Smart Chain queda como segundo despliegue posible usando el mismo diseno.
No puede seleccionarse para implementacion mientras el emisor oficial no
publique una direccion verificable del token elegido en BSC. No se aceptan como
fuente blogs, tutoriales, resultados de buscador ni una pagina de explorador sin
enlace canonico del emisor.

## Fuentes Verificadas

- Base docs: Base Mainnet usa `chain_id = 8453` y moneda gas ETH.
- Circle docs: USDC en Base usa
  `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- BNB Chain docs: BSC Mainnet usa `chain_id = 56` y moneda gas BNB.
- Tether docs: la pagina oficial lista BNB Smart Chain, pero en su seccion BSC
  publica XAUt y no publica una direccion USDt. Por eso BSC/USDT esta bloqueado
  por fuente de token.
- Circle docs: la lista oficial de contratos USDC publica Base, pero no publica
  BNB Smart Chain. Por eso BSC/USDC no puede tratarse como USDC nativo de Circle.
- OpenZeppelin docs: usar utilidades ERC20 y seguridad probadas, incluyendo
  SafeERC20, Pausable/ReentrancyGuard cuando aplique.

## Flujo Nuevo

1. Negocio aprobado elige paquete.
2. Backend crea `credit_purchase` con estado `pending_payment`.
3. Backend crea y guarda `purchase_ref` aleatorio de 32 bytes.
4. Frontend obtiene la wallet pagadora conectada por el negocio.
5. Backend crea y firma una autorizacion que amarra:
   - `purchase_ref`;
   - wallet pagadora;
   - monto exacto;
   - chain;
   - contrato;
   - version;
   - expiracion.
6. Backend devuelve al frontend:
   - chain autorizada;
   - contrato NODO autorizado;
   - token autorizado;
   - monto esperado;
   - `purchase_ref`;
   - autorizacion firmada;
   - expiracion;
   - instrucciones de wallet.
7. Wallet aprueba el token al contrato y llama `pay(authorization, signature)`.
8. Contrato:
   - verifica que no este pausado;
   - verifica que la firma sea de NODO;
   - verifica wallet pagadora, monto, chain, contrato, version y expiracion;
   - verifica `purchase_ref` no usado;
   - transfiere token permitido desde el pagador hacia tesoreria NODO;
   - emite `NodoCreditPaymentReceived`.
9. Watcher/backend lee solo eventos del contrato oficial.
10. Backend verifica:
   - chain;
   - direccion del contrato;
   - token;
   - treasury;
   - `purchase_ref`;
   - wallet pagadora esperada;
   - monto exacto o politica contratada;
   - confirmaciones;
   - purchase no terminal;
   - evento/tx/log no usado.
   - Transfer ERC20 canonico del token oficial desde `payer` hacia `treasury`
     por el monto declarado en el evento.
11. Backend acredita exactamente una vez en la transaccion PostgreSQL de wallet
    y ledger.

## No Custodia P2P

Este contrato recibe pagos de negocios por creditos publicitarios NODO.

No recibe, guarda, mueve, protege ni garantiza fondos entre cliente y negocio.
No es escrow. No procesa remesas. No garantiza entrega ni recuperacion.

## Contrato Smart Contract

Nombre de trabajo: `NODOCreditPaymentVaultSigned`.

Propiedades:

- EVM compatible.
- No upgradeable en MVP.
- `treasury` immutable.
- `acceptedToken` immutable.
- `contractVersion` constante.
- `authorizedSigner` rotatable por owner/multisig.
- `purchase_ref` single-use.
- autorizacion EIP-712 firmada por NODO.
- Pausable por owner/multisig.
- No acepta native ETH/BNB.
- No soporta pagos parciales sumados automaticamente.
- No soporta varios tokens en el mismo despliegue.

Evento canonico:

```solidity
event NodoCreditPaymentReceived(
    bytes32 indexed purchaseRef,
    address indexed payer,
    address indexed token,
    address treasury,
    uint256 amount,
    uint256 chainId,
    uint256 contractVersion,
    uint256 validUntil
);
```

Funcion principal:

```solidity
function pay(PaymentAuthorization calldata authorization, bytes calldata signature) external;
```

La funcion usa `SafeERC20.safeTransferFrom(msg.sender, treasury,
authorization.amount)`.

## Por Que No Usar Solo Wallet Directa

Wallet directa es simple para humanos, pero mala para acreditacion automatica:

- el hash es publico;
- cualquiera puede copiarlo;
- el transfer no contiene el id de compra;
- el backend tiene que inferir intencion;
- una wallet cambiada por error o por ataque puede desviar pagos.

El contrato arregla eso porque el pago queda marcado con un `purchase_ref`
emitido por el contrato oficial NODO y autorizado por una firma backend que
amarra monto, wallet pagadora, chain, contrato, version y expiracion.

El backend deriva el negocio y la compra desde `purchase_ref`; nunca desde
`payer`, `tx_hash` o datos enviados por el frontend. Un hash publico sin el
evento oficial y el ref esperado no puede acreditar.

## BSC / BNB

El contrato puede desplegarse en BNB Smart Chain porque BSC es EVM compatible.

Para activar BSC se requiere un slice separado y una nueva revision de fuentes:

- confirmar token oficial y contrato exacto;
- definir si sera USDT, USDC bridged o solo manual;
- definir proveedor RPC y confirmaciones;
- desplegar contrato BSC testnet;
- probar con wallet temporal;
- actualizar contratos NODO y UI sin mezclar Base con BSC;
- no aceptar token por simbolo o nombre.

## Comparacion MVP

| Opcion | Fuente de red | Fuente de token | Estado 52A | Riesgo principal |
| --- | --- | --- | --- | --- |
| Base + USDC | Base oficial, chain 8453 | Circle publica USDC Base | Recomendada | Menor familiaridad que BSC para algunos negocios y gas en ETH. |
| BSC + USDt | BNB Chain oficial, chain 56 | Tether no publica USDt BSC en su lista vigente | `BLOCKED_BY_TOKEN_SOURCE` | Elegir una direccion no certificada por emisor. |
| BSC + USDC | BNB Chain oficial, chain 56 | Circle no lista BSC | `BLOCKED_BY_TOKEN_SOURCE` | Activo bridged o de tercero presentado como USDC nativo. |
| Binance Pay/Connect | Proveedor externo | Depende de onboarding y contrato del proveedor | Futuro, fuera de 52A | Custodia/proveedor, credenciales, fees y dependencia contractual. |

Binance Pay/Connect no es equivalente al contrato propio. Solo puede evaluarse
en un slice de proveedor con documentacion oficial del producto, onboarding de
merchant, autenticacion, webhooks, costos y terminos aplicables.

## Limites Del Diseno Simple

- Un `purchase_ref` debe ser aleatorio, no secuencial, de 32 bytes y entregarse
  solo al negocio autenticado de la compra.
- Un tercero que vea una transaccion pendiente no puede usar el ref con otra
  wallet, otro monto, otra red, otro contrato o fuera de expiracion sin romper
  la firma.
- Un pago parcial no deberia pasar el contrato si el amount firmado es exacto.
  Si por comportamiento de token o integracion surge una inconsistencia, el
  backend debe mandar la compra a `under_review`.
- El evento del vault no basta por si solo: el verifier confirma tambien el log
  ERC20 del token immutable hacia treasury.
- El contrato no guarda saldo intencionalmente; `sweepToTreasury` solo recupera
  tokens enviados directamente al contrato y nunca acredita creditos.

## Archivos Que Puede Tocar Un Builder En 52A

Solo documentos de contrato:

- `control_plane/09_SLICES/slice_52A_crypto_credit_payment_contract/*`
- Si Owner aprueba reconciliacion:
  - `control_plane/03_DOMAIN_RULES/ONCHAIN_CREDIT_TOPUPS_MASTER.md`
  - `control_plane/06_API_CONTRACTS/CREDITS_API.md`
  - `control_plane/04_DATA/DATA_MODEL_MASTER.md`
  - `control_plane/04_DATA/DATABASE_CONSTRAINTS.md`
  - `control_plane/04_DATA/ENUMS_AND_STATUS_MASTER.md`

## Archivos Prohibidos En 52A

- Runtime backend.
- Frontend.
- Migrations.
- Smart contract Solidity.
- Railway, Cloudflare, Supabase, Upstash config.
- Wallet real, fondos reales, staging mutante o produccion.

## Estado De Readiness

52A no declara `READY_FOR_REAL_USE`.

Para construir Solidity hace falta Owner approval sobre:

1. red MVP;
2. token MVP;
3. tesoreria temporal;
4. toolkit Solidity;
5. auditoria externa o al menos review independiente;
6. smoke con monto pequeno y rollback.
