# NODO Credit Payment Vault V2 - Signed Authorization Review

> Revision historica de diseno. No define la API business ni la politica
> legacy despues de 52C-S0. Para esas reglas usar `CREDITS_API.md` y los API
> contracts 52A/52C.

Estado: `SIGNED_AUTH_CONTRACT_DRAFT_READY_FOR_OWNER_REVIEW`

Este documento reescribe el borrador del contrato con la mejora que discutimos:
el contrato no acepta un `purchaseRef` y un monto inventados por quien llama.
Ahora exige una autorizacion firmada por NODO.

Es el diseno recomendado para la siguiente fase del slice 52A. No es runtime,
no es migracion, no es deploy y no configura wallets reales.

## Idea Simple

El flujo correcto seria:

```text
Backend NODO crea compra
  "wallet X puede pagar exactamente 100 USDC con REF123 hasta tal hora"
          |
          v
Backend NODO firma esa autorizacion
          |
          v
Negocio envia la autorizacion al contrato
          |
          v
Contrato verifica:
  - la firma es de NODO
  - la wallet que paga es la autorizada
  - el monto es exacto
  - la red es la correcta
  - el contrato es el correcto
  - la autorizacion no expiro
  - la referencia no fue usada
          |
          v
Contrato mueve USDC directo a treasury y emite evento
          |
          v
Backend espera confirmaciones y acredita una sola vez
```

La diferencia clave contra el borrador V1:

```text
V1:
pay(purchaseRef, amount)
El usuario decide purchaseRef y amount.

V2:
pay(authorization, signature)
NODO decide purchaseRef, payer, amount, expiry, chain y contract.
El contrato solo acepta si la firma valida todo eso.
```

## Codigo Educativo

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";

contract NODOCreditPaymentVaultSigned is
    Ownable2Step,
    Pausable,
    ReentrancyGuard,
    EIP712
{
    using SafeERC20 for IERC20;

    uint256 public constant CONTRACT_VERSION = 2;

    IERC20 public immutable acceptedToken;
    address public immutable treasury;
    address public authorizedSigner;

    mapping(bytes32 => bool) public usedPurchaseRefs;

    bytes32 private constant PAYMENT_AUTHORIZATION_TYPEHASH = keccak256(
        "PaymentAuthorization(bytes32 purchaseRef,address payer,uint256 amount,uint256 validUntil,uint256 chainId,address verifyingContract,uint256 contractVersion)"
    );

    struct PaymentAuthorization {
        bytes32 purchaseRef;
        address payer;
        uint256 amount;
        uint256 validUntil;
        uint256 chainId;
        address verifyingContract;
        uint256 contractVersion;
    }

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

    event AuthorizedSignerUpdated(
        address indexed previousSigner,
        address indexed newSigner
    );

    event SweptToTreasury(
        address indexed token,
        uint256 amount
    );

    error ZeroAddress();
    error ZeroPurchaseRef();
    error ZeroAmount();
    error PurchaseRefAlreadyUsed();
    error AuthorizationExpired();
    error PayerMismatch();
    error ChainMismatch();
    error ContractMismatch();
    error VersionMismatch();
    error InvalidAuthorizationSignature();
    error NativePaymentNotAccepted();
    error OwnershipRenounceDisabled();

    constructor(
        IERC20 acceptedToken_,
        address treasury_,
        address initialOwner_,
        address authorizedSigner_
    )
        Ownable(initialOwner_)
        EIP712("NODOCreditPaymentVault", "2")
    {
        if (address(acceptedToken_) == address(0)) revert ZeroAddress();
        if (treasury_ == address(0)) revert ZeroAddress();
        if (initialOwner_ == address(0)) revert ZeroAddress();
        if (authorizedSigner_ == address(0)) revert ZeroAddress();

        acceptedToken = acceptedToken_;
        treasury = treasury_;
        authorizedSigner = authorizedSigner_;
    }

    function pay(
        PaymentAuthorization calldata authorization,
        bytes calldata signature
    )
        external
        whenNotPaused
        nonReentrant
    {
        _validateAuthorization(authorization, signature);

        usedPurchaseRefs[authorization.purchaseRef] = true;

        acceptedToken.safeTransferFrom(
            msg.sender,
            treasury,
            authorization.amount
        );

        emit NodoCreditPaymentReceived(
            authorization.purchaseRef,
            msg.sender,
            address(acceptedToken),
            treasury,
            authorization.amount,
            block.chainid,
            CONTRACT_VERSION,
            authorization.validUntil
        );
    }

    function setAuthorizedSigner(address newSigner) external onlyOwner {
        if (newSigner == address(0)) revert ZeroAddress();

        address previousSigner = authorizedSigner;
        authorizedSigner = newSigner;

        emit AuthorizedSignerUpdated(previousSigner, newSigner);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function sweepToTreasury(IERC20 token, uint256 amount) external onlyOwner {
        if (address(token) == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        token.safeTransfer(treasury, amount);

        emit SweptToTreasury(address(token), amount);
    }

    function renounceOwnership() public override onlyOwner {
        revert OwnershipRenounceDisabled();
    }

    receive() external payable {
        revert NativePaymentNotAccepted();
    }

    fallback() external payable {
        revert NativePaymentNotAccepted();
    }

    function _validateAuthorization(
        PaymentAuthorization calldata authorization,
        bytes calldata signature
    ) private view {
        if (authorization.purchaseRef == bytes32(0)) revert ZeroPurchaseRef();
        if (authorization.amount == 0) revert ZeroAmount();
        if (authorization.payer != msg.sender) revert PayerMismatch();
        if (block.timestamp >= authorization.validUntil) revert AuthorizationExpired();
        if (authorization.chainId != block.chainid) revert ChainMismatch();
        if (authorization.verifyingContract != address(this)) revert ContractMismatch();
        if (authorization.contractVersion != CONTRACT_VERSION) revert VersionMismatch();
        if (usedPurchaseRefs[authorization.purchaseRef]) revert PurchaseRefAlreadyUsed();

        bytes32 structHash = keccak256(
            abi.encode(
                PAYMENT_AUTHORIZATION_TYPEHASH,
                authorization.purchaseRef,
                authorization.payer,
                authorization.amount,
                authorization.validUntil,
                authorization.chainId,
                authorization.verifyingContract,
                authorization.contractVersion
            )
        );

        bytes32 digest = _hashTypedDataV4(structHash);
        address recoveredSigner = ECDSA.recover(digest, signature);

        if (recoveredSigner != authorizedSigner) {
            revert InvalidAuthorizationSignature();
        }
    }
}
```

## Que Soluciona Este V2

### 1. Quien puede generar `purchaseRef`

El `purchaseRef` puede verse, pero no basta con verlo. Para usarlo hace falta
una firma valida de NODO que lo amarre a wallet, monto, red, contrato y tiempo.

### 2. Front-running y griefing

En V1, si alguien encontraba una referencia valida podia intentar consumirla con
un monto incorrecto. En V2, si no es la wallet autorizada y no usa el monto
exacto, el contrato rechaza.

Esto no elimina todos los ataques posibles. Si la wallet del negocio esta
comprometida, el atacante puede actuar como esa wallet. Ese problema ya no es
del contrato, es seguridad de la wallet del usuario.

### 3. Monto vinculado on-chain

`amount` va dentro de la autorizacion firmada. El usuario no puede cambiar
100 USDC por 1 USDC sin invalidar la firma.

### 4. Payer vinculado on-chain

`payer` va firmado y ademas debe coincidir con `msg.sender`. Si otra wallet
intenta pagar con esa autorizacion, falla.

### 5. Expiracion

`validUntil` evita que una autorizacion vieja siga funcionando indefinidamente.
La frontera es estricta: al llegar a ese timestamp, la autorizacion ya expiro.

### 6. Chain y contrato correcto

La autorizacion incluye `chainId`, `verifyingContract` y `contractVersion`.
Ademas, EIP-712 incluye dominio de firma. Esto reduce replay entre redes,
contratos o versiones.

### 7. Idempotencia

`usedPurchaseRefs[purchaseRef]` evita que la misma referencia se use dos veces
en el contrato.

El backend todavia debe tener su propia idempotencia. El contrato evita doble
pago aceptado con la misma referencia; el backend evita doble credito.

### 8. Autenticidad del evento

El backend no debe confiar en "vi un evento con ese nombre". Debe verificar:

```text
chain_id esperado
contract_address esperado
token esperado
treasury esperado
purchase_ref esperado
payer esperado
amount esperado
transaction receipt confirmado
Transfer ERC-20 real hacia treasury
confirmaciones suficientes
```

### 9. Allowance UX

Este diseno sigue usando el flujo ERC-20 normal:

```text
1. approve(contract, amount)
2. pay(authorization, signature)
```

Eso puede sentirse menos comodo que Binance Pay, pero es mas controlable para
NODO. Mas adelante se podria estudiar `permit` si el token y la wallet lo
soportan bien, pero no lo meteria en el MVP sin pruebas.

### 10. Owner y multisig

El owner puede:

- pausar pagos;
- reanudar pagos;
- rotar `authorizedSigner`;
- hacer sweep a treasury si alguien envia tokens al contrato por error.

El owner no puede cambiar `acceptedToken` ni `treasury`, porque son `immutable`.

Recomendacion: owner debe ser multisig, no una wallet caliente del backend.

### 11. `renounceOwnership`

Se bloquea. Si se renuncia ownership por accidente, se pierde capacidad de
pausar, reanudar o rotar signer. Para NODO eso seria peligroso.

### 12. OpenZeppelin versionada

El contrato debe fijar version exacta de OpenZeppelin en el lockfile antes de
compilar y auditar. No se debe usar una version flotante.

## Que NO Soluciona Solo El Contrato

El contrato no puede decidir si se acreditan creditos en NODO. Eso sigue siendo
responsabilidad del backend.

El backend debe:

- crear compra con monto esperado;
- crear `purchaseRef` aleatorio y no adivinable;
- asociar compra a business_id;
- registrar wallet esperada;
- firmar solo compras validas;
- esperar confirmaciones;
- manejar reorgs;
- acreditar exactamente una vez;
- mandar a `under_review` cualquier caso raro;
- no guardar llaves de treasury u owner.

## Nuevos Secretos

Este diseno introduce un secreto nuevo:

```text
authorized signer private key
```

Ese signer no debe mover fondos. Solo firma autorizaciones para que el contrato
acepte pagos.

Aun asi debe protegerse:

- no va en el repo;
- no va al frontend;
- no se imprime en logs;
- idealmente vive en secret manager o servicio de firma;
- debe poder rotarse con `setAuthorizedSigner`;
- cada rotacion debe generar alerta Admin.

La treasury private key y la owner/multisig private key no deben vivir en el
backend.

## Pruebas Minimas Antes De Pensar En Testnet

### Unitarias

- constructor rechaza direcciones cero;
- pago correcto transfiere exactamente el monto a treasury;
- firma invalida falla;
- signer incorrecto falla;
- payer incorrecto falla;
- monto cambiado falla;
- chain incorrecta falla;
- contrato incorrecto falla;
- version incorrecta falla;
- autorizacion expirada falla;
- replay de `purchaseRef` falla;
- pago nativo falla;
- pausa bloquea pago;
- unpause vuelve a permitir pago;
- owner puede rotar signer;
- no-owner no puede rotar signer;
- `renounceOwnership` falla;
- sweep solo envia a treasury y no emite evento acreditable.

### Fuzzing / invariants

- nunca se emiten dos pagos exitosos para el mismo `purchaseRef`;
- nunca sale token a una direccion distinta de treasury;
- si `NodoCreditPaymentReceived` se emite, existio `Transfer` real del token;
- datos alterados invalidan la firma;
- signer antiguo deja de funcionar despues de rotacion.

### Backend

- compra queda `pending` hasta confirmaciones suficientes;
- reorg revierte o espera sin acreditar;
- evento de otro contrato se ignora;
- token distinto se ignora;
- monto menor/mayor va a politica definida;
- replay de watcher no duplica creditos;
- misma transaccion no puede acreditar dos compras;
- evento `sweep` nunca acredita.

## Decision Que Falta

Antes de implementar de verdad hay que decidir:

```text
toolkit: Foundry o Hardhat
red inicial: Base
token inicial: USDC nativo publicado por Circle
treasury temporal: wallet de pruebas
owner temporal: idealmente multisig/test multisig
authorized signer: wallet separada, rotatable
confirmaciones: numero exacto para staging y mainnet
expiracion: por ejemplo 15 o 30 minutos
auditoria externa: si/no antes de fondos reales
```

## Fuentes Oficiales Usadas

- OpenZeppelin Contracts 5.x Cryptography: EIP712 y ECDSA.
  https://docs.openzeppelin.com/contracts/5.x/api/utils/cryptography
- OpenZeppelin Contracts 5.x ERC20: IERC20 y SafeERC20.
  https://docs.openzeppelin.com/contracts/5.x/api/token/erc20
- OpenZeppelin Contracts 5.x Utils: Pausable y ReentrancyGuard.
  https://docs.openzeppelin.com/contracts/5.x/api/utils
- OpenZeppelin Contracts 5.x Access: Ownable y Ownable2Step.
  https://docs.openzeppelin.com/contracts/5.x/api/access
- Solidity Contracts docs: receive/fallback para rechazar pago nativo.
  https://docs.soliditylang.org/en/latest/contracts.html

## Estado Honesto

Este V2 es mucho mejor que el V1 simple para NODO, porque reduce referencias
robadas, montos alterados, pagos desde wallet incorrecta y autorizaciones viejas.

Pero todavia no es `READY_FOR_REAL_USE`. Falta:

- escoger toolkit;
- escribir contrato real en `contracts/`;
- pin exacto de dependencias;
- pruebas unitarias/fuzz/invariants;
- despliegue testnet;
- verificacion del backend contra eventos reales;
- smoke con wallet temporal;
- revision externa antes de fondos reales.
