from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from app.core.errors import ApiError
from app.modules.credits.models import BASE_MAINNET_CHAIN_ID, BASE_USDC_CONTRACT_ADDRESS, BASE_USDC_DECIMALS, CreditPurchaseRecord

TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def normalize_evm(value: str | None) -> str | None:
    return value.lower() if value else None


def validate_evm_address(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 42 or not normalized.startswith("0x"):
        raise ApiError("VALIDATION_ERROR", status_code=422)
    try:
        int(normalized[2:], 16)
    except ValueError as exc:
        raise ApiError("VALIDATION_ERROR", status_code=422) from exc
    return normalized


def validate_tx_hash(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 66 or not normalized.startswith("0x"):
        raise ApiError("ONCHAIN_TX_INVALID", status_code=400)
    try:
        int(normalized[2:], 16)
    except ValueError as exc:
        raise ApiError("ONCHAIN_TX_INVALID", status_code=400) from exc
    return normalized


def price_to_usdc_units(price_usd: Decimal) -> int:
    return int((price_usd * Decimal(10**BASE_USDC_DECIMALS)).to_integral_exact())


def _topic_address(topic: str) -> str:
    raw = topic.lower().removeprefix("0x")
    return "0x" + raw[-40:]


@dataclass(frozen=True)
class OnchainVerificationResult:
    chain_id: int
    token_contract_address: str
    destination_wallet_address: str
    tx_hash: str
    tx_from_address: str | None
    tx_to_address: str | None
    tx_amount_units: int | None
    tx_block_number: int | None
    tx_log_index: int | None
    confirmations: int
    verification_status: str
    error_code: str | None = None


class BaseUsdcVerifier:
    def verify(
        self,
        *,
        tx_hash: str,
        expected_amount_units: int,
        destination_wallet_address: str,
        min_confirmations: int,
        latest_block_number: int | None = None,
    ) -> OnchainVerificationResult:
        raise NotImplementedError


def normalize_credit_verification(
    *,
    purchase: CreditPurchaseRecord,
    verification: OnchainVerificationResult,
    submitted_tx_hash: str,
    min_confirmations: int,
    now: datetime,
) -> OnchainVerificationResult:
    """Fail closed if a verifier returns a result outside the purchase contract."""

    normalized_tx_hash = validate_tx_hash(submitted_tx_hash)
    expected_token = normalize_evm(purchase.token_contract_address)
    expected_destination = normalize_evm(purchase.destination_wallet_address)

    if verification.tx_hash.lower() != normalized_tx_hash:
        return _verification_failure(verification, "ONCHAIN_VERIFICATION_FAILED")
    if purchase.chain_id != BASE_MAINNET_CHAIN_ID or verification.chain_id != purchase.chain_id:
        return _verification_failure(verification, "ONCHAIN_WRONG_CHAIN")
    if (
        expected_token != BASE_USDC_CONTRACT_ADDRESS
        or normalize_evm(verification.token_contract_address) != expected_token
        or not expected_destination
        or normalize_evm(verification.destination_wallet_address) != expected_destination
        or (verification.tx_to_address is not None and normalize_evm(verification.tx_to_address) != expected_destination)
    ):
        return _verification_failure(verification, "ONCHAIN_WRONG_TOKEN_OR_WALLET")
    if verification.error_code:
        return verification
    if verification.verification_status != "verified":
        return verification
    if (
        purchase.expected_amount_units is None
        or verification.tx_amount_units is None
        or verification.tx_amount_units < purchase.expected_amount_units
        or verification.confirmations < min_confirmations
        or verification.tx_log_index is None
    ):
        return _verification_failure(verification, "ONCHAIN_VERIFICATION_FAILED")
    if purchase.expires_at is not None and now >= purchase.expires_at:
        return replace(verification, verification_status="under_review", error_code=None)
    return verification


def _verification_failure(verification: OnchainVerificationResult, code: str) -> OnchainVerificationResult:
    return replace(verification, verification_status="verification_failed", error_code=code)


class JsonRpcBaseUsdcVerifier(BaseUsdcVerifier):
    def __init__(self, *, rpc_url: str | None, timeout_seconds: int) -> None:
        self._rpc_url = rpc_url
        self._timeout_seconds = timeout_seconds
        self._cached_chain_id: int | None = None
        self._rpc_call_count = 0

    @property
    def rpc_call_count(self) -> int:
        return self._rpc_call_count

    def latest_block_number(self) -> int:
        return int(self._rpc("eth_blockNumber", []), 16)

    def verify(
        self,
        *,
        tx_hash: str,
        expected_amount_units: int,
        destination_wallet_address: str,
        min_confirmations: int,
        latest_block_number: int | None = None,
    ) -> OnchainVerificationResult:
        if not self._rpc_url:
            raise ApiError("ONCHAIN_RPC_UNAVAILABLE", status_code=503)
        normalized_tx = validate_tx_hash(tx_hash)
        destination = validate_evm_address(destination_wallet_address)
        chain_id = self._chain_id()
        if chain_id != BASE_MAINNET_CHAIN_ID:
            return _failed(normalized_tx, destination, chain_id, "ONCHAIN_WRONG_CHAIN")
        receipt = self._rpc("eth_getTransactionReceipt", [normalized_tx])
        if receipt is None:
            raise ApiError("ONCHAIN_TX_NOT_FOUND", status_code=404)
        receipt_status = str(receipt.get("status") or "").lower()
        if receipt_status != "0x1":
            block_number = int(receipt["blockNumber"], 16) if receipt.get("blockNumber") else None
            return _failed(normalized_tx, destination, chain_id, "ONCHAIN_TX_FAILED", block_number=block_number)
        latest_block = latest_block_number if latest_block_number is not None else self.latest_block_number()
        block_number = int(receipt["blockNumber"], 16)
        confirmations = max(0, latest_block - block_number + 1)
        transfer = self._find_usdc_transfer(receipt, destination)
        if transfer is None:
            return _failed(normalized_tx, destination, chain_id, "ONCHAIN_WRONG_TOKEN_OR_WALLET", block_number=block_number, confirmations=confirmations)
        amount_units = int(transfer["data"], 16)
        log_index = int(transfer["logIndex"], 16)
        tx_from = normalize_evm(receipt.get("from"))
        tx_to = _topic_address(transfer["topics"][2])
        if confirmations < min_confirmations:
            status = "pending_onchain_confirmation"
        elif amount_units < expected_amount_units:
            status = "under_review"
        else:
            status = "verified"
        return OnchainVerificationResult(
            chain_id=chain_id,
            token_contract_address=BASE_USDC_CONTRACT_ADDRESS,
            destination_wallet_address=destination,
            tx_hash=normalized_tx,
            tx_from_address=tx_from,
            tx_to_address=tx_to,
            tx_amount_units=amount_units,
            tx_block_number=block_number,
            tx_log_index=log_index,
            confirmations=confirmations,
            verification_status=status,
        )

    def _chain_id(self) -> int:
        if self._cached_chain_id is None:
            self._cached_chain_id = int(self._rpc("eth_chainId", []), 16)
        return self._cached_chain_id

    def _rpc(self, method: str, params: list[object]) -> object:
        self._rpc_call_count += 1
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
        request = urllib.request.Request(self._rpc_url or "", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310 - RPC URL is configured server-side.
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError("ONCHAIN_RPC_UNAVAILABLE", status_code=503) from exc
        if data.get("error"):
            raise ApiError("ONCHAIN_RPC_UNAVAILABLE", status_code=503)
        return data.get("result")

    def _find_usdc_transfer(self, receipt: dict, destination: str) -> dict | None:
        for log in receipt.get("logs", []):
            topics = [str(topic).lower() for topic in log.get("topics", [])]
            if len(topics) < 3:
                continue
            if str(log.get("address", "")).lower() != BASE_USDC_CONTRACT_ADDRESS:
                continue
            if topics[0] != TRANSFER_EVENT_TOPIC:
                continue
            if _topic_address(topics[2]) != destination:
                continue
            return log
        return None


def _failed(tx_hash: str, destination: str, chain_id: int, code: str, *, block_number: int | None = None, confirmations: int = 0) -> OnchainVerificationResult:
    return OnchainVerificationResult(
        chain_id=chain_id,
        token_contract_address=BASE_USDC_CONTRACT_ADDRESS,
        destination_wallet_address=destination,
        tx_hash=tx_hash,
        tx_from_address=None,
        tx_to_address=None,
        tx_amount_units=None,
        tx_block_number=block_number,
        tx_log_index=None,
        confirmations=confirmations,
        verification_status="verification_failed",
        error_code=code,
    )
