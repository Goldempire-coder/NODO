from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


CREDIT_PACKAGES = {
    "starter": {"credits": 5, "price_usd": Decimal("10.00")},
    "pro": {"credits": 15, "price_usd": Decimal("25.00")},
    "business": {"credits": 50, "price_usd": Decimal("75.00")},
    "enterprise": {"credits": 200, "price_usd": Decimal("250.00")},
}
TESTNET_CREDIT_PACKAGE_PRICE_SCALE = Decimal("0.01")
TESTNET_CREDIT_PACKAGE_PRICE_QUANTUM = Decimal("0.01")
TESTNET_CREDIT_PACKAGE_PRICE_ENVS = {"local", "test", "staging"}
BASE_MAINNET_CHAIN_ID = 8453
BASE_MAINNET_NETWORK = "base_mainnet"
BASE_USDC_TOKEN_SYMBOL = "USDC"
BASE_USDC_CONTRACT_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
BASE_USDC_DECIMALS = 6
BASE_SEPOLIA_CHAIN_ID = 84532
BASE_SEPOLIA_NETWORK = "base_sepolia"
BASE_SEPOLIA_USDC_CONTRACT_ADDRESS = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
ONCHAIN_CREDIT_LEDGER_REASON = "base_usdc_onchain_verified"


@dataclass(frozen=True)
class CreditPaymentNetworkProfile:
    network: str
    chain_id: int
    display_name: str
    token_symbol: str
    token_contract_address: str
    token_decimals: int
    is_testnet: bool


CREDIT_PAYMENT_NETWORK_PROFILES = {
    BASE_MAINNET_NETWORK: CreditPaymentNetworkProfile(
        network=BASE_MAINNET_NETWORK,
        chain_id=BASE_MAINNET_CHAIN_ID,
        display_name="Base",
        token_symbol=BASE_USDC_TOKEN_SYMBOL,
        token_contract_address=BASE_USDC_CONTRACT_ADDRESS,
        token_decimals=BASE_USDC_DECIMALS,
        is_testnet=False,
    ),
    BASE_SEPOLIA_NETWORK: CreditPaymentNetworkProfile(
        network=BASE_SEPOLIA_NETWORK,
        chain_id=BASE_SEPOLIA_CHAIN_ID,
        display_name="Base Sepolia",
        token_symbol=BASE_USDC_TOKEN_SYMBOL,
        token_contract_address=BASE_SEPOLIA_USDC_CONTRACT_ADDRESS,
        token_decimals=BASE_USDC_DECIMALS,
        is_testnet=True,
    ),
}


def credit_payment_network_profile(value: str | None) -> CreditPaymentNetworkProfile | None:
    return CREDIT_PAYMENT_NETWORK_PROFILES.get((value or "").strip().lower())


def contract_credit_package(
    package_code: str,
    *,
    app_env: str,
    network_profile: CreditPaymentNetworkProfile | None,
) -> dict[str, int | Decimal] | None:
    package = CREDIT_PACKAGES.get(package_code)
    if package is None:
        return None

    price_usd = package["price_usd"]
    if (
        network_profile is not None
        and network_profile.is_testnet
        and app_env.strip().lower() in TESTNET_CREDIT_PACKAGE_PRICE_ENVS
    ):
        price_usd = (price_usd * TESTNET_CREDIT_PACKAGE_PRICE_SCALE).quantize(
            TESTNET_CREDIT_PACKAGE_PRICE_QUANTUM
        )

    return {"credits": package["credits"], "price_usd": price_usd}

PURCHASE_METHODS = {"stripe_checkout", "zelle_manual_admin_approved", "usdt_manual_admin_approved", "base_usdc_onchain", "base_usdc_contract"}
PURCHASE_STATUSES = {
    "created",
    "pending_payment",
    "pending_manual_review",
    "pending_onchain_confirmation",
    "detected",
    "verified",
    "credited",
    "under_review",
    "paid",
    "approved",
    "rejected",
    "failed",
    "expired",
    "verification_failed",
}
CONTRACT_NON_TERMINAL_PURCHASE_STATUSES = {
    "pending_payment",
    "pending_onchain_confirmation",
    "detected",
    "under_review",
}
REFERRAL_CODE_STATUSES = {"active", "disabled"}
REFERRAL_EVENT_STATUSES = {"pending", "approved", "rewarded", "rejected"}
ALLOWED_PROOF_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_PROOF_SIZE_BYTES = 5 * 1024 * 1024


@dataclass
class CreditPurchaseRecord:
    id: str
    business_id: str
    package_code: str
    credits_amount: int
    price_usd: Decimal
    payment_method: str
    status: str
    idempotency_key: str | None = None
    stripe_checkout_session_id: str | None = None
    stripe_payment_intent_id: str | None = None
    stripe_event_id: str | None = None
    manual_payment_reference: str | None = None
    manual_tx_hash: str | None = None
    manual_network: str | None = None
    chain_id: int | None = None
    network: str | None = None
    token_symbol: str | None = None
    token_contract_address: str | None = None
    token_decimals: int | None = None
    expected_amount_units: int | None = None
    destination_wallet_address: str | None = None
    onchain_purchase_ref: str | None = None
    onchain_payer_address: str | None = None
    payment_contract_address: str | None = None
    payment_contract_version: int | None = None
    payment_authorization_expires_at: datetime | None = None
    payment_authorization_digest: str | None = None
    payment_authorization_signature: str | None = None
    payment_authorization_signer_address: str | None = None
    payment_authorization_signer_version: str | None = None
    payment_authorization_signed_at: datetime | None = None
    tx_hash: str | None = None
    tx_amount_units: int | None = None
    tx_from_address: str | None = None
    tx_to_address: str | None = None
    tx_block_number: int | None = None
    tx_log_index: int | None = None
    confirmations: int | None = None
    verification_source: str | None = None
    verification_status: str | None = None
    proof_file_id: str | None = None
    approved_by_admin_id: str | None = None
    rejected_by_admin_id: str | None = None
    admin_note: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    paid_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    failed_at: datetime | None = None
    expired_at: datetime | None = None
    detected_at: datetime | None = None
    verified_at: datetime | None = None
    credited_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass
class ReferralCodeRecord:
    id: str
    business_id: str
    code: str
    status: str = "active"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    disabled_at: datetime | None = None


@dataclass
class ReferralEventRecord:
    id: str
    referral_code_id: str
    referrer_business_id: str
    referred_business_id: str
    status: str
    related_credit_purchase_id: str | None = None
    credits_awarded: int = 0
    reject_reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    approved_at: datetime | None = None
    rewarded_at: datetime | None = None
    rejected_at: datetime | None = None


@dataclass(frozen=True)
class ReferralApprovalResult:
    event: ReferralEventRecord | None
    outcome: str
    created: bool
    business_approved: bool = False
    event_changed: bool = False
