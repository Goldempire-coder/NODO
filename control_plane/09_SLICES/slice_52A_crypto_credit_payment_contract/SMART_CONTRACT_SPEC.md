# SMART_CONTRACT_SPEC.md

## Contrato

Nombre: `NODOCreditPaymentVaultSigned`

Objetivo: recibir pagos ERC20 por creditos publicitarios NODO y emitir un evento
que vincule el pago a una compra backend, aceptando solo autorizaciones firmadas
por NODO.

## Constructor

```solidity
constructor(
    address acceptedToken_,
    address treasury_,
    address owner_,
    address authorizedSigner_
)
```

Reglas:

- `acceptedToken_ != address(0)`
- `treasury_ != address(0)`
- `owner_ != address(0)`
- `authorizedSigner_ != address(0)`
- `acceptedToken` immutable
- `treasury` immutable
- `authorizedSigner` solo firma autorizaciones; no mueve fondos
- `owner` solo administra pausa, signer y recuperacion segura hacia treasury
- usar `Ownable2Step` para que un cambio de owner requiera aceptacion explicita

## Estado

```solidity
IERC20 public immutable acceptedToken;
address public immutable treasury;
uint256 public constant CONTRACT_VERSION = 2;
address public authorizedSigner;
mapping(bytes32 => bool) public usedPurchaseRefs;
```

## Funcion Principal

```solidity
function pay(
    PaymentAuthorization calldata authorization,
    bytes calldata signature
) external whenNotPaused nonReentrant
```

Validaciones:

- `authorization.purchaseRef != bytes32(0)`
- `authorization.amount > 0`
- `authorization.payer == msg.sender`
- `authorization.validUntil > block.timestamp`
- `authorization.chainId == block.chainid`
- `authorization.verifyingContract == address(this)`
- `authorization.contractVersion == CONTRACT_VERSION`
- `usedPurchaseRefs[authorization.purchaseRef] == false`
- `signature` recupera `authorizedSigner`

Efectos:

1. marca `usedPurchaseRefs[authorization.purchaseRef] = true`;
2. transfiere `authorization.amount` de `msg.sender` a `treasury`;
3. emite `NodoCreditPaymentReceived`.

Si `safeTransferFrom` falla, la transaccion revierte y `purchaseRef` no queda
usado.

La frontera de expiracion es estricta: cuando `block.timestamp` alcanza
`validUntil`, la autorizacion ya vencio.

El contrato no conoce paquetes ni business id. Si conoce, por firma, el monto
exacto, la wallet pagadora, la red, el contrato, la version y la expiracion.
El backend sigue siendo autoridad de creditos, paquetes, ledger y auditoria.

## Autorizacion Firmada

```solidity
struct PaymentAuthorization {
    bytes32 purchaseRef;
    address payer;
    uint256 amount;
    uint256 validUntil;
    uint256 chainId;
    address verifyingContract;
    uint256 contractVersion;
}
```

`PAYMENT_AUTHORIZATION_TYPEHASH` debe ser fijo y cubierto por pruebas. La firma
usa EIP-712 para que una autorizacion no pueda reutilizarse entre redes,
contratos o versiones.

## Evento Canonico

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

El backend debe ignorar cualquier evento que no venga de la direccion oficial
del contrato NODO configurada para esa red.

Ademas debe comprobar en el mismo receipt el evento `Transfer` del
`acceptedToken`, desde `payer` hacia `treasury`, por el mismo `amount`. La firma
del evento NODO, el simbolo del token o los campos enviados por frontend no son
autoridad suficiente.

## Generacion De Purchase Ref Y Firma

El backend genera un `bytes32` criptograficamente aleatorio. No se deriva de
business id, purchase id, timestamp ni contador. El backend liga el ref a una
sola compra antes de entregarlo al negocio autenticado.

El backend firma solo despues de conocer la wallet pagadora conectada y el monto
esperado. La firma no contiene private keys de treasury u owner. El contrato
evita reutilizacion global del ref. El backend mantiene ademas la unicidad
durable por compra, ref y evento. El pagador on-chain no define a quien se
acreditan los creditos; esa relacion se deriva solo de la compra backend.

## Pausa

Funciones:

```solidity
function pause() external onlyOwner;
function unpause() external onlyOwner;
```

Uso:

- detener cobros si hay bug, token incorrecto, wallet equivocada, RPC comprometido
  o ataque operativo;
- no cambia compras ya acreditadas;
- no acredita ni devuelve dinero.

## Recuperacion De Tokens Enviados Por Error

ERC20 permite transferencias directas a contratos sin llamar `pay`. Esas
transferencias no deben acreditar creditos.

Funcion permitida solo para rescatar balances atrapados hacia la misma
tesoreria immutable:

```solidity
function sweepToTreasury(address token) external onlyOwner nonReentrant;
```

Reglas:

- destino siempre `treasury`;
- emite `NodoVaultSweep`;
- backend nunca acredita por sweep;
- runbook Admin requerido para cualquier caso real.

Evento:

```solidity
event NodoVaultSweep(address indexed token, address indexed treasury, uint256 amount);
```

## Rechazos

El contrato debe revertir con errores custom:

- `ZeroPurchaseRef`
- `ZeroAmount`
- `PurchaseRefAlreadyUsed`
- `AuthorizationExpired`
- `PayerMismatch`
- `ChainMismatch`
- `ContractMismatch`
- `VersionMismatch`
- `InvalidAuthorizationSignature`
- `ZeroAddress`
- `NativePaymentNotAccepted`
- `OwnershipRenounceDisabled`

## Native ETH / BNB

```solidity
receive() external payable { revert NativePaymentNotAccepted(); }
fallback() external payable { revert NativePaymentNotAccepted(); }
```

Esto rechaza envios normales. Un saldo nativo forzado por comportamiento EVM no
debe acreditar creditos y queda fuera del flujo de pago MVP.

## No Incluir En MVP

- Upgradeable proxy.
- Multiples tokens en un contrato.
- Multiples treasuries.
- Admin que cambie `treasury`.
- Admin que cambie `acceptedToken`.
- Calculo de paquetes on-chain.
- Refund automatico.
- Pagos nativos ETH/BNB.
- Bridge.
- Comisiones variables.

## Motivo De No Usar Upgradeable En MVP

Un proxy agrega poder administrativo y riesgo de upgrade malicioso. Para NODO,
el contrato de cobro puede ser pequeno y versionado por despliegue. Si cambia
wallet, token o red, se despliega un contrato nuevo y el backend cambia la
configuracion mediante release auditado.
