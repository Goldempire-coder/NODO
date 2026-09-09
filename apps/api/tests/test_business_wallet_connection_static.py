from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_business_credit_purchase_uses_connected_wallet_without_manual_input() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert "Paga con MetaMask." in screen
    assert "void connectWallet()" not in screen
    assert "Preparar autorizacion" not in screen
    assert "NODO no ve ni guarda tu clave privada." in screen
    assert "MetaMask mostrara cada paso antes de confirmarlo." in screen
    assert "Esta wallet será la que firma y paga." in screen
    assert "value={payerWalletAddress}" not in screen
    assert "setPayerWalletAddress" not in screen
    assert 'placeholder="0x... wallet en Base"' not in screen


def test_credit_dashboard_buy_button_stays_visually_ready_while_balance_refreshes() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    dashboard = screen.split("export function CreditsDashboardScreen", 1)[1].split(
        "export function BuyCreditsScreen",
        1,
    )[0]
    buy_button = dashboard.split('onClick={() => void openBuyCredits()}', 1)[0].rsplit("<button", 1)[1]

    assert "mini-action-button--filled" in buy_button
    assert "disabled={busy}" not in buy_button


def test_business_credit_authorization_uses_only_connected_base_account() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")
    helper = _read("apps/web/src/lib/wallet/testnetCreditPayment.ts")

    assert "useInjectedWallet" in page
    assert "connectedWalletAddress" in page
    assert "walletIsExpectedNetwork" in page
    assert "claimCreditHandoff" in page
    assert "requirePayableTestnetCreditPayment" in helper
    assert "TESTNET_PAYMENT_WALLET_MISMATCH" in helper
    assert "payerWalletAddress" not in page
    assert "setPayerWalletAddress" not in page


def test_injected_wallet_adapter_handles_account_and_chain_changes() -> None:
    adapter = _read("apps/web/src/lib/wallet/eip1193.ts")
    wallet_hook = _read("apps/web/src/hooks/business-mini-app/useInjectedWallet.ts")
    payment_page = _read("apps/web/src/app/business/credit-payment/page.tsx")

    assert 'method: "eth_requestAccounts"' in adapter
    assert 'method: "eth_chainId"' in adapter
    assert "BASE_SEPOLIA_CHAIN_ID = 84532" in adapter
    assert 'BASE_SEPOLIA_CHAIN_ID_HEX = "0x14a34"' in adapter
    assert 'method: "wallet_switchEthereumChain"' in adapter
    assert 'method: "wallet_addEthereumChain"' in adapter
    assert "expectedNetwork" in wallet_hook
    assert "switchWalletToExpectedNetwork" in wallet_hook
    assert "switchingWalletNetwork" in wallet_hook
    assert '.on("accountsChanged"' in wallet_hook
    assert '.on("chainChanged"' in wallet_hook
    assert '.removeListener("accountsChanged"' in wallet_hook
    assert '.removeListener("chainChanged"' in wallet_hook
    invalidate_block = payment_page.split("useInjectedWallet(() => {", 1)[1].split(
        "}, expectedNetwork)", 1
    )[0]
    assert "setPaymentDetail(null)" in invalidate_block
    assert 'setPaymentStep("wallet")' in invalidate_block
    assert "localStorage" not in adapter
    assert "localStorage" not in wallet_hook
    assert "console." not in adapter
    assert "console." not in wallet_hook


def test_telegram_can_refresh_pending_contract_purchase_without_wallet_provider() -> None:
    credits_hook = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    continue_block = credits_hook.split("const continuePendingBaseUsdcPayment", 1)[1].split("const loadCreditDashboard", 1)[0]

    assert 'walletProviderStatus !== "available"' not in continue_block
    assert "!connectedWalletAddress" not in continue_block
    assert "!walletIsExpectedNetwork" not in continue_block
    assert "getBusinessCreditPurchase" in continue_block
    assert "data.payment?.payer_wallet_address" in continue_block
    assert "clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId)" in continue_block


def test_wallet_connection_runtime_has_no_payment_or_dependency_expansion() -> None:
    source = "\n".join(
        (
            _read("apps/web/src/lib/wallet/eip1193.ts"),
            _read("apps/web/src/hooks/business-mini-app/useInjectedWallet.ts"),
            _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts"),
            _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx"),
        )
    ).lower()

    for forbidden in (
        "tx_hash",
        "submitbusinessbaseusdctxhash",
        "approve(",
        "pay(",
        "@reown/",
        "@walletconnect/",
        'from "wagmi"',
        'from "viem"',
        "setinterval(",
    ):
        assert forbidden not in source
