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
NODO_CREDIT_PAYMENT_RECEIVED_TOPIC = "0x4a8ea99d41259460c1f4047610d05603c61ed4d4e69634212c638286b9db9b8f"


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


def _address_topic(value: str) -> str:
    return "0x" + "0" * 24 + validate_evm_address(value).removeprefix("0x")


def _hex_int(value: object | None) -> int | None:
    if value is None:
        return None
    return int(str(value), 16)


def _decode_abi_address(slot: str) -> str:
    raw = slot.lower().removeprefix("0x")
    return "0x" + raw[-40:]


def _decode_contract_payment_log(log: dict) -> dict | None:
    topics = [str(topic).lower() for topic in log.get("topics", [])]
    if len(topics) < 4 or topics[0] != NODO_CREDIT_PAYMENT_RECEIVED_TOPIC:
        return None
    raw_data = str(log.get("data") or "0x").lower().removeprefix("0x")
    if len(raw_data) != 64 * 5:
        return None
    slots = [raw_data[index : index + 64] for index in range(0, len(raw_data), 64)]
    return {
        "purchase_ref": topics[1],
        "payer": _topic_address(topics[2]),
        "token": _topic_address(topics[3]),
        "treasury": _decode_abi_address(slots[0]),
        "amount": int(slots[1], 16),
        "chain_id": int(slots[2], 16),
        "contract_version": int(slots[3], 16),
        "valid_until": int(slots[4], 16),
    }


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


@dataclass(frozen=True)
class _ContractPaymentExpectation:
    purchase: CreditPurchaseRecord
    contract: str
    token: str
    destination: str
    payer: str
    purchase_ref: str


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

    def find_contract_payment(
        self,
        *,
        purchase: CreditPurchaseRecord,
        min_confirmations: int,
        latest_block_number: int | None = None,
        lookback_blocks: int = 5000,
    ) -> OnchainVerificationResult | None:
        raise NotImplementedError

    def find_contract_payments(
        self,
        *,
        purchases: list[CreditPurchaseRecord],
        min_confirmations: int,
        latest_block_number: int | None = None,
        lookback_blocks: int = 5000,
    ) -> dict[str, OnchainVerificationResult | None]:
        return {
            purchase.id: self.find_contract_payment(
                purchase=purchase,
                min_confirmations=min_confirmations,
                latest_block_number=latest_block_number,
                lookback_blocks=lookback_blocks,
            )
            for purchase in purchases
        }


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
    if purchase.chain_id is None or verification.chain_id != purchase.chain_id:
        return _verification_failure(verification, "ONCHAIN_WRONG_CHAIN")
    expected_payer = normalize_evm(purchase.onchain_payer_address)
    if expected_payer and normalize_evm(verification.tx_from_address) != expected_payer:
        return _verification_failure(verification, "ONCHAIN_VERIFICATION_FAILED")
    if (
        not expected_token
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
    if purchase.payment_method != "base_usdc_contract" and purchase.expires_at is not None and now >= purchase.expires_at:
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

    def find_contract_payment(
        self,
        *,
        purchase: CreditPurchaseRecord,
        min_confirmations: int,
        latest_block_number: int | None = None,
        lookback_blocks: int = 5000,
    ) -> OnchainVerificationResult | None:
        return self.find_contract_payments(
            purchases=[purchase],
            min_confirmations=min_confirmations,
            latest_block_number=latest_block_number,
            lookback_blocks=lookback_blocks,
        ).get(purchase.id)

    def find_contract_payments(
        self,
        *,
        purchases: list[CreditPurchaseRecord],
        min_confirmations: int,
        latest_block_number: int | None = None,
        lookback_blocks: int = 5000,
    ) -> dict[str, OnchainVerificationResult | None]:
        if not self._rpc_url:
            raise ApiError("ONCHAIN_RPC_UNAVAILABLE", status_code=503)
        if not purchases:
            return {}
        chain_id = self._chain_id()
        latest_block = latest_block_number if latest_block_number is not None else self.latest_block_number()
        from_block = max(0, latest_block - max(1, lookback_blocks))
        results: dict[str, OnchainVerificationResult | None] = {purchase.id: None for purchase in purchases}
        expectations = [self._contract_payment_expectation(purchase) for purchase in purchases]
        grouped: dict[str, list[_ContractPaymentExpectation]] = {}
        for expectation in expectations:
            if expectation.purchase.chain_id != chain_id:
                raise ApiError("ONCHAIN_WRONG_CHAIN", status_code=409)
            grouped.setdefault(expectation.contract, []).append(expectation)
        for contract, contract_expectations in grouped.items():
            purchase_refs = [expectation.purchase_ref for expectation in contract_expectations]
            topics_ref_filter: str | list[str] = purchase_refs[0] if len(purchase_refs) == 1 else purchase_refs
            logs = self._rpc(
                "eth_getLogs",
                [
                    {
                        "address": contract,
                        "fromBlock": hex(from_block),
                        "toBlock": hex(latest_block),
                        "topics": [NODO_CREDIT_PAYMENT_RECEIVED_TOPIC, topics_ref_filter],
                    }
                ],
            )
            by_ref = {expectation.purchase_ref: expectation for expectation in contract_expectations}
            sorted_logs = sorted(
                (log for log in logs if isinstance(log, dict)),
                key=lambda log: (_hex_int(log.get("blockNumber")) or 0, _hex_int(log.get("logIndex")) or 0),
            )
            for log in sorted_logs:
                decoded = _decode_contract_payment_log(log)
                if decoded is None:
                    continue
                expectation = by_ref.get(decoded["purchase_ref"])
                if expectation is None or results[expectation.purchase.id] is not None:
                    continue
                verification = self._contract_log_to_verification(
                    purchase=expectation.purchase,
                    log=log,
                    contract=expectation.contract,
                    token=expectation.token,
                    destination=expectation.destination,
                    payer=expectation.payer,
                    latest_block=latest_block,
                    min_confirmations=min_confirmations,
                )
                if verification is not None:
                    results[expectation.purchase.id] = verification
        return results

    @staticmethod
    def _contract_payment_expectation(purchase: CreditPurchaseRecord) -> _ContractPaymentExpectation:
        contract = validate_evm_address(purchase.payment_contract_address or "")
        token = validate_evm_address(purchase.token_contract_address or "")
        destination = validate_evm_address(purchase.destination_wallet_address or "")
        payer = validate_evm_address(purchase.onchain_payer_address or "")
        purchase_ref = (purchase.onchain_purchase_ref or "").lower()
        if len(purchase_ref) != 66 or not purchase_ref.startswith("0x"):
            raise ApiError("ONCHAIN_VERIFICATION_FAILED", status_code=409)
        try:
            int(purchase_ref[2:], 16)
        except ValueError as exc:
            raise ApiError("ONCHAIN_VERIFICATION_FAILED", status_code=409) from exc
        if purchase.chain_id is None:
            raise ApiError("ONCHAIN_WRONG_CHAIN", status_code=409)
        return _ContractPaymentExpectation(
            purchase=purchase,
            contract=contract,
            token=token,
            destination=destination,
            payer=payer,
            purchase_ref=purchase_ref,
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

    def _contract_log_to_verification(
        self,
        *,
        purchase: CreditPurchaseRecord,
        log: dict,
        contract: str,
        token: str,
        destination: str,
        payer: str,
        latest_block: int,
        min_confirmations: int,
    ) -> OnchainVerificationResult | None:
        tx_hash = str(log.get("transactionHash") or "").lower()
        if not tx_hash:
            return None
        tx_hash = validate_tx_hash(tx_hash)
        block_number = _hex_int(log.get("blockNumber"))
        log_index = _hex_int(log.get("logIndex"))
        if block_number is None or log_index is None:
            return None
        confirmations = max(0, latest_block - block_number + 1)
        decoded = _decode_contract_payment_log(log)
        if decoded is None:
            return _failed_for_purchase(purchase, tx_hash, "ONCHAIN_VERIFICATION_FAILED", block_number=block_number, confirmations=confirmations)
        receipt = self._rpc("eth_getTransactionReceipt", [tx_hash])
        if receipt is None:
            raise ApiError("ONCHAIN_TX_NOT_FOUND", status_code=404)
        receipt_status = str(receipt.get("status") or "").lower()
        if receipt_status != "0x1":
            return _failed_for_purchase(purchase, tx_hash, "ONCHAIN_TX_FAILED", block_number=block_number, confirmations=confirmations)
        expected_valid_until = int(purchase.payment_authorization_expires_at.timestamp()) if purchase.payment_authorization_expires_at else None
        expected_amount = purchase.expected_amount_units
        expected = (
            str(log.get("address", "")).lower() == contract
            and decoded["purchase_ref"] == (purchase.onchain_purchase_ref or "").lower()
            and decoded["payer"] == payer
            and decoded["token"] == token
            and decoded["treasury"] == destination
            and decoded["amount"] == expected_amount
            and decoded["chain_id"] == purchase.chain_id
            and decoded["contract_version"] == purchase.payment_contract_version
            and decoded["valid_until"] == expected_valid_until
        )
        if not expected:
            return _failed_for_purchase(purchase, tx_hash, "ONCHAIN_VERIFICATION_FAILED", block_number=block_number, confirmations=confirmations)
        if not self._receipt_has_contract_event(receipt, log_index, contract, purchase.onchain_purchase_ref or ""):
            return _failed_for_purchase(purchase, tx_hash, "ONCHAIN_VERIFICATION_FAILED", block_number=block_number, confirmations=confirmations)
        if not self._receipt_has_transfer(receipt, token=token, payer=payer, destination=destination, amount_units=expected_amount or 0):
            return _failed_for_purchase(purchase, tx_hash, "ONCHAIN_WRONG_TOKEN_OR_WALLET", block_number=block_number, confirmations=confirmations)
        status = "pending_onchain_confirmation" if confirmations < min_confirmations else "verified"
        return OnchainVerificationResult(
            chain_id=purchase.chain_id,
            token_contract_address=token,
            destination_wallet_address=destination,
            tx_hash=tx_hash,
            tx_from_address=payer,
            tx_to_address=destination,
            tx_amount_units=expected_amount,
            tx_block_number=block_number,
            tx_log_index=log_index,
            confirmations=confirmations,
            verification_status=status,
        )

    def _receipt_has_contract_event(self, receipt: dict, log_index: int, contract: str, purchase_ref: str) -> bool:
        for log in receipt.get("logs", []):
            topics = [str(topic).lower() for topic in log.get("topics", [])]
            if _hex_int(log.get("logIndex")) != log_index:
                continue
            if str(log.get("address", "")).lower() != contract:
                continue
            if len(topics) < 2 or topics[0] != NODO_CREDIT_PAYMENT_RECEIVED_TOPIC:
                continue
            if topics[1] != purchase_ref.lower():
                continue
            return True
        return False

    def _receipt_has_transfer(self, receipt: dict, *, token: str, payer: str, destination: str, amount_units: int) -> bool:
        for log in receipt.get("logs", []):
            topics = [str(topic).lower() for topic in log.get("topics", [])]
            if len(topics) < 3:
                continue
            if str(log.get("address", "")).lower() != token:
                continue
            if topics[0] != TRANSFER_EVENT_TOPIC:
                continue
            if topics[1] != _address_topic(payer) or topics[2] != _address_topic(destination):
                continue
            if int(str(log.get("data") or "0x0"), 16) != amount_units:
                continue
            return True
        return False


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


def _failed_for_purchase(
    purchase: CreditPurchaseRecord,
    tx_hash: str,
    code: str,
    *,
    block_number: int | None = None,
    confirmations: int = 0,
) -> OnchainVerificationResult:
    return OnchainVerificationResult(
        chain_id=purchase.chain_id or 0,
        token_contract_address=normalize_evm(purchase.token_contract_address) or "",
        destination_wallet_address=normalize_evm(purchase.destination_wallet_address) or "",
        tx_hash=tx_hash,
        tx_from_address=normalize_evm(purchase.onchain_payer_address),
        tx_to_address=normalize_evm(purchase.destination_wallet_address),
        tx_amount_units=None,
        tx_block_number=block_number,
        tx_log_index=None,
        confirmations=confirmations,
        verification_status="verification_failed",
        error_code=code,
    )
