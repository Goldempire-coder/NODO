from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_business_credit_purchase_uses_connected_wallet_without_manual_input() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert "Conectar wallet" in screen
    assert "Abrir MetaMask para probar conexión" in screen
    assert "NODO no puede conectar tu wallet desde aqui" in screen
    assert "Conecta la wallet desde donde pagarás." in screen
    assert "NODO no ve ni guarda tu clave privada." in screen
    assert "Esta wallet será la que firma y paga." in screen
    assert 'disabled={connectingWallet || walletProviderStatus === "checking"}' in screen
    assert 'walletProviderStatus !== "available"' not in screen
    assert "value={payerWalletAddress}" not in screen
    assert "setPayerWalletAddress" not in screen
    assert 'placeholder="0x... wallet en Base"' not in screen


def test_business_credit_authorization_uses_only_connected_base_account() -> None:
    hook = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")

    assert "useInjectedWallet" in hook
    assert "connectedWalletAddress" in hook
    assert "walletIsBase" in hook
    assert "startBusinessBaseUsdcPayment" in hook
    assert "connectedWalletAddress," in hook
    assert "payerWalletAddress" not in hook
    assert "setPayerWalletAddress" not in hook


def test_injected_wallet_adapter_handles_account_and_chain_changes() -> None:
    adapter = _read("apps/web/src/lib/wallet/eip1193.ts")
    wallet_hook = _read("apps/web/src/hooks/business-mini-app/useInjectedWallet.ts")
    credits_hook = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")

    assert 'method: "eth_requestAccounts"' in adapter
    assert 'method: "eth_chainId"' in adapter
    assert "BASE_MAINNET_CHAIN_ID = 8453" in adapter
    assert '.on("accountsChanged"' in wallet_hook
    assert '.on("chainChanged"' in wallet_hook
    assert '.removeListener("accountsChanged"' in wallet_hook
    assert '.removeListener("chainChanged"' in wallet_hook
    assert "invalidatePreparedCreditPayment" in credits_hook
    assert "setSelectedCreditPayment(null)" in credits_hook
    assert "setSelectedCreditPurchase(null)" in credits_hook
    invalidate_block = credits_hook.split("const invalidatePreparedCreditPayment", 1)[1].split("const {", 1)[0]
    assert "setPendingCreditPurchase(null)" in invalidate_block
    assert "clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey)" in invalidate_block
    assert "localStorage" not in adapter
    assert "localStorage" not in wallet_hook
    assert "console." not in adapter
    assert "console." not in wallet_hook


def test_pending_contract_purchase_requires_the_current_connected_base_wallet() -> None:
    credits_hook = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    continue_block = credits_hook.split("const continuePendingBaseUsdcPayment", 1)[1].split("const loadCreditDashboard", 1)[0]

    assert 'walletProviderStatus !== "available"' in continue_block
    assert "!connectedWalletAddress" in continue_block
    assert "!walletIsBase" in continue_block
    assert "const preparedWallet = getConnectedWalletSnapshot()" in continue_block
    assert "data.payment?.payer_wallet_address" in continue_block
    assert "paymentWallet !== preparedWallet.address" in continue_block
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
