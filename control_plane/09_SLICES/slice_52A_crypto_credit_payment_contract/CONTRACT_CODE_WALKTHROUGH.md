# CONTRACT_CODE_WALKTHROUGH.md

Estado: `SUPERSEDED_BY_SIGNED_AUTH_V2`

Este archivo muestra como se veria el contrato minimo para estudiar la idea con
calma. No es runtime aprobado, no se debe desplegar, no mueve fondos y no
declara readiness.

Advertencia: este borrador V1 queda solo como explicacion historica. No debe
copiarse para implementacion. El contrato oficial del slice 52A ahora es
`NODOCreditPaymentVaultSigned`, documentado en `SMART_CONTRACT_SPEC.md` y
ampliado en `CONTRACT_SIGNED_AUTH_V2_REVIEW.md`.

Motivo: V1 permite que quien llama envie `purchaseRef` y `amount`. Eso no
comprueba por si mismo que NODO autorizo esa wallet, ese monto, esa red, ese
contrato y esa expiracion.

## Idea Simple

El contrato es una caja registradora de NODO:

1. NODO crea una compra y genera un `purchaseRef`.
2. El negocio paga usando ese `purchaseRef`.
3. El contrato envia el USDC directo a la tesoreria de NODO.
4. El contrato emite un evento publico.
5. El backend acredita creditos solo si ese evento coincide con la compra.

## Codigo De Estudio

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract NODOCreditPaymentVault is Ownable2Step, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public immutable acceptedToken;
    address public immutable treasury;
    uint256 public constant CONTRACT_VERSION = 1;

    mapping(bytes32 => bool) public usedPurchaseRefs;

    event NodoCreditPaymentReceived(
        bytes32 indexed purchaseRef,
        address indexed payer,
        address indexed token,
        address treasury,
        uint256 amount,
        uint256 chainId,
        uint256 contractVersion
    );

    event NodoVaultSweep(
        address indexed token,
        address indexed treasury,
        uint256 amount
    );

    error ZeroAddress();
    error ZeroPurchaseRef();
    error ZeroAmount();
    error PurchaseRefAlreadyUsed();
    error NativePaymentNotAccepted();

    constructor(
        address acceptedToken_,
        address treasury_,
        address owner_
    ) Ownable(owner_) {
        if (acceptedToken_ == address(0)) revert ZeroAddress();
        if (treasury_ == address(0)) revert ZeroAddress();
        if (owner_ == address(0)) revert ZeroAddress();

        acceptedToken = IERC20(acceptedToken_);
        treasury = treasury_;
    }

    function pay(bytes32 purchaseRef, uint256 amount)
        external
        whenNotPaused
        nonReentrant
    {
        if (purchaseRef == bytes32(0)) revert ZeroPurchaseRef();
        if (amount == 0) revert ZeroAmount();
        if (usedPurchaseRefs[purchaseRef]) revert PurchaseRefAlreadyUsed();

        usedPurchaseRefs[purchaseRef] = true;

        acceptedToken.safeTransferFrom(msg.sender, treasury, amount);

        emit NodoCreditPaymentReceived(
            purchaseRef,
            msg.sender,
            address(acceptedToken),
            treasury,
            amount,
            block.chainid,
            CONTRACT_VERSION
        );
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function sweepToTreasury(address token)
        external
        onlyOwner
        nonReentrant
    {
        if (token == address(0)) revert ZeroAddress();

        IERC20 rescueToken = IERC20(token);
        uint256 balance = rescueToken.balanceOf(address(this));

        rescueToken.safeTransfer(treasury, balance);

        emit NodoVaultSweep(token, treasury, balance);
    }

    receive() external payable {
        revert NativePaymentNotAccepted();
    }

    fallback() external payable {
        revert NativePaymentNotAccepted();
    }
}
```

## Que Hace Cada Parte

`acceptedToken`

El token permitido. En el primer diseno seria USDC en Base. No se puede cambiar
dentro del contrato.

`treasury`

La wallet donde entra el dinero de NODO. Tampoco se puede cambiar dentro del
contrato. Si algun dia cambia la tesoreria, se despliega otro contrato.

`purchaseRef`

Es el codigo unico de una compra. Evita que un negocio use el hash de otro.

`usedPurchaseRefs`

Marca cada compra como usada. Asi el mismo pago/ref no se puede usar dos veces.

`pay`

Es la funcion principal. Recibe el `purchaseRef`, toma el token autorizado desde
la wallet del negocio y lo manda directo a `treasury`.

`pause / unpause`

Permite detener pagos nuevos si hay un problema. No acredita ni mueve dinero.

`sweepToTreasury`

Solo rescata tokens enviados por error al contrato y los manda a la misma
tesoreria. El backend nunca debe acreditar creditos por un sweep.

`receive / fallback`

Rechazan ETH/BNB nativo. El MVP solo acepta el token ERC20 configurado.

## Lo Que Este Contrato No Hace

- No calcula paquetes.
- No decide creditos.
- No guarda fondos de Cliente/Negocio.
- No funciona como escrow.
- No cambia tasa.
- No recibe Zelle, Pago Movil, USDT TRC20 ni Binance Pay.
- No guarda private keys.
- No puede cambiar token ni treasury.

## Videos Para Entender

Estos videos son para aprender conceptos, no para copiar direcciones ni tomar
decisiones de seguridad:

- OpenZeppelin tutorial playlist:
  https://www.youtube.com/playlist?list=PLbbtODcOYIoFdQ37ydykQNO-MNGER6mtd
- Solidity beginner to expert course:
  https://www.youtube.com/watch?v=M576WGiDBdQ
- ERC20 transfer/approve/transferFrom:
  https://www.youtube.com/watch?v=-5j6Ho0Bkfk
- Crear ERC20 con OpenZeppelin:
  https://www.youtube.com/watch?v=DILDtLTrx_s
- Base + OpenZeppelin/Foundry example:
  https://www.youtube.com/watch?v=uzUM-aYv9sI

## Fuentes Oficiales Que Si Mandan

- OpenZeppelin ERC20/SafeERC20:
  https://docs.openzeppelin.com/contracts/5.x/api/token/erc20
- OpenZeppelin Access/Ownable2Step:
  https://docs.openzeppelin.com/contracts/5.x/api/access
- OpenZeppelin Utils/Pausable/ReentrancyGuard:
  https://docs.openzeppelin.com/contracts/5.x/api/utils
- Solidity language docs:
  https://docs.soliditylang.org/
- Base docs:
  https://docs.base.org/base-chain/quickstart/connecting-to-base
- Circle USDC contract addresses:
  https://developers.circle.com/stablecoins/usdc-contract-addresses

## Proxima Revision Antes De Implementar

Antes de convertir esto en runtime real:

1. elegir Foundry o Hardhat;
2. crear pruebas locales;
3. probar con mock USDC;
4. desplegar en testnet;
5. usar wallet temporal;
6. auditar el contrato;
7. conectar backend solo despues de aprobar otra fase.

No usar este contrato con fondos reales sin pruebas, auditoria y aprobacion
separada.
