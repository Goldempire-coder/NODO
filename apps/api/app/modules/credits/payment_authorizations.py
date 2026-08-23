from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data

from app.core.errors import ApiError
from app.modules.credits.onchain import validate_evm_address

EIP712_DOMAIN_NAME = "NODOCreditPaymentVaultSigned"
EIP712_DOMAIN_VERSION = "2"
ZERO_ADDRESS = "0x" + "0" * 40


@dataclass(frozen=True)
class PaymentAuthorizationSnapshot:
    purchase_ref: str
    payer: str
    amount: int
    valid_until: int
    chain_id: int
    verifying_contract: str
    contract_version: int


@dataclass(frozen=True)
class SignedPaymentAuthorization:
    typed_data: dict[str, Any]
    digest: str
    signature: str
    signer_address: str


def normalize_payment_address(value: str) -> str:
    normalized = validate_evm_address(value)
    if normalized == ZERO_ADDRESS:
        raise ApiError("VALIDATION_ERROR", status_code=422)
    return normalized


def new_purchase_ref() -> str:
    purchase_ref = "0x" + secrets.token_hex(32)
    while purchase_ref == "0x" + "0" * 64:
        purchase_ref = "0x" + secrets.token_hex(32)
    return purchase_ref


def build_payment_authorization_typed_data(snapshot: PaymentAuthorizationSnapshot) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "PaymentAuthorization": [
                {"name": "purchaseRef", "type": "bytes32"},
                {"name": "payer", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "validUntil", "type": "uint256"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
                {"name": "contractVersion", "type": "uint256"},
            ],
        },
        "primaryType": "PaymentAuthorization",
        "domain": {
            "name": EIP712_DOMAIN_NAME,
            "version": EIP712_DOMAIN_VERSION,
            "chainId": snapshot.chain_id,
            "verifyingContract": snapshot.verifying_contract,
        },
        "message": {
            "purchaseRef": snapshot.purchase_ref,
            "payer": snapshot.payer,
            "amount": snapshot.amount,
            "validUntil": snapshot.valid_until,
            "chainId": snapshot.chain_id,
            "verifyingContract": snapshot.verifying_contract,
            "contractVersion": snapshot.contract_version,
        },
    }


def sign_payment_authorization(
    snapshot: PaymentAuthorizationSnapshot,
    *,
    signer_key: str,
    configured_signer_address: str,
) -> SignedPaymentAuthorization:
    try:
        expected_signer = normalize_payment_address(configured_signer_address)
        actual_signer = Account.from_key(signer_key).address.lower()
        if actual_signer != expected_signer:
            raise ValueError("configured signer does not match key")
        typed_data = build_payment_authorization_typed_data(snapshot)
        signable = encode_typed_data(full_message=typed_data)
        signed = Account.sign_message(signable, private_key=signer_key)
    except (TypeError, ValueError, ApiError) as exc:
        raise ApiError(
            "CRYPTO_PAYMENT_SIGNER_UNAVAILABLE",
            message="No pudimos preparar el pago en este momento.",
            status_code=503,
        ) from exc
    return SignedPaymentAuthorization(
        typed_data=typed_data,
        digest=signed.message_hash.to_0x_hex(),
        signature=signed.signature.to_0x_hex(),
        signer_address=actual_signer,
    )


def authorization_is_expired(*, valid_until: int, now: datetime) -> bool:
    return int(now.timestamp()) >= valid_until
