// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { Ownable2Step } from "@openzeppelin/contracts/access/Ownable2Step.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { ECDSA } from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import { EIP712 } from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import { Pausable } from "@openzeppelin/contracts/utils/Pausable.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

contract NODOCreditPaymentVaultSigned is EIP712, Ownable2Step, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    struct PaymentAuthorization {
        bytes32 purchaseRef;
        address payer;
        uint256 amount;
        uint256 validUntil;
        uint256 chainId;
        address verifyingContract;
        uint256 contractVersion;
    }

    IERC20 public immutable acceptedToken;
    address public immutable treasury;
    uint256 public constant CONTRACT_VERSION = 2;
    bytes32 public constant PAYMENT_AUTHORIZATION_TYPEHASH = keccak256(
        "PaymentAuthorization(bytes32 purchaseRef,address payer,uint256 amount,uint256 validUntil,uint256 chainId,address verifyingContract,uint256 contractVersion)"
    );

    address public authorizedSigner;
    mapping(bytes32 => bool) public usedPurchaseRefs;

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
    event AuthorizedSignerUpdated(address indexed previousSigner, address indexed newSigner);
    event NodoVaultSweep(address indexed token, address indexed treasury, uint256 amount);

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
        address acceptedToken_,
        address treasury_,
        address owner_,
        address authorizedSigner_
    )
        EIP712("NODOCreditPaymentVaultSigned", "2")
        Ownable(owner_)
    {
        if (acceptedToken_ == address(0)) revert ZeroAddress();
        if (treasury_ == address(0)) revert ZeroAddress();
        if (owner_ == address(0)) revert ZeroAddress();
        if (authorizedSigner_ == address(0)) revert ZeroAddress();

        acceptedToken = IERC20(acceptedToken_);
        treasury = treasury_;
        authorizedSigner = authorizedSigner_;

        emit AuthorizedSignerUpdated(address(0), authorizedSigner_);
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
        acceptedToken.safeTransferFrom(msg.sender, treasury, authorization.amount);

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

    function sweepToTreasury(address token) external onlyOwner nonReentrant {
        if (token == address(0)) revert ZeroAddress();

        uint256 amount = IERC20(token).balanceOf(address(this));
        if (amount == 0) revert ZeroAmount();

        IERC20(token).safeTransfer(treasury, amount);
        emit NodoVaultSweep(token, treasury, amount);
    }

    function renounceOwnership() public view override onlyOwner {
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
    )
        private
        view
    {
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
        (address recoveredSigner, ECDSA.RecoverError recoverError,) = ECDSA.tryRecover(digest, signature);
        if (recoverError != ECDSA.RecoverError.NoError || recoveredSigner != authorizedSigner) {
            revert InvalidAuthorizationSignature();
        }
    }
}
