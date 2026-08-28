from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_business_credits_offers_metamask_handoff_as_the_single_payment_cta() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")

    assert "Abrir MetaMask" in screen
    assert "Abrir MetaMask para pagar en prueba" in screen
    assert "void connectWallet()" not in screen
    assert "openMetaMaskCreditHandoff" in model


def test_metamask_probe_uses_a_fixed_public_route_without_private_context() -> None:
    helper = _read("apps/web/src/lib/wallet/metamaskHandoff.ts")
    page = _read("apps/web/src/app/business/wallet-probe/page.tsx")

    assert 'const WALLET_PROBE_PATH = "/business/wallet-probe/"' in helper
    assert "https://link.metamask.io/dapp/" in helper
    assert "https://metamask.app.link/dapp/" not in helper
    assert "window.location.origin" in helper
    assert "telegramWebApp?.openLink" in helper
    assert "telegramWebApp.openLink(deeplink)" in helper
    assert "window.location.assign" in helper
    assert "probe.search" not in helper
    assert "probe.hash" not in helper
    assert "useTelegramAuth" not in page
    assert "Esta prueba no cobra, no firma pagos y no mueve fondos." in page

    private_markers = (
        "accessToken",
        "refreshToken",
        "initData",
        "tgWebAppData",
        "business_id",
        "purchase_id",
        "package_code",
    )
    for marker in private_markers:
        assert marker not in helper


def test_metamask_probe_restricts_origins_to_nodo_staging_and_local_dev() -> None:
    helper = _read("apps/web/src/lib/wallet/metamaskHandoff.ts")

    assert (
        'const NODO_PROBE_HTTPS_ORIGINS = new Set(["https://nodo-staging.pages.dev"]);'
        in helper
    )
    assert 'url.protocol === "https:" && NODO_PROBE_HTTPS_ORIGINS.has(url.origin)' in helper
    assert 'if (url.protocol === "https:")' not in helper
    assert 'return url.protocol === "http:"' in helper
    assert 'url.hostname === "localhost"' in helper
    assert 'url.hostname === "127.0.0.1"' in helper
    assert 'url.hostname === "[::1]"' in helper
    assert "source.username" in helper
    assert "source.password" in helper
    assert "source.search" in helper
    assert "source.hash" in helper
    assert "source.pathname !== \"/\"" in helper
    assert "WALLET_PROBE_ORIGIN_INVALID" in helper


def test_wallet_probe_is_read_only_and_dependency_free() -> None:
    source = "\n".join(
        (
            _read("apps/web/src/app/business/wallet-probe/page.tsx"),
            _read("apps/web/src/lib/wallet/metamaskHandoff.ts"),
        )
    ).lower()

    forbidden = (
        "approve(",
        "pay(",
        "eth_sendtransaction",
        "personal_sign",
        "eth_signtypeddata",
        "tx_hash",
        "accesstoken",
        "refreshtoken",
        "initdata",
        "@reown/",
        "@walletconnect/",
        'from "wagmi"',
        'from "viem"',
        "localstorage",
        "sessionstorage",
        "setinterval(",
    )
    for marker in forbidden:
        assert marker not in source


def test_wallet_probe_can_request_base_sepolia_without_payment_actions() -> None:
    adapter = _read("apps/web/src/lib/wallet/eip1193.ts")
    page = _read("apps/web/src/app/business/wallet-probe/page.tsx")

    assert 'BASE_SEPOLIA_CHAIN_ID_HEX = "0x14a34"' in adapter
    assert 'method: "wallet_switchEthereumChain"' in adapter
    assert 'method: "wallet_addEthereumChain"' in adapter
    assert "https://sepolia.base.org" in adapter
    assert "https://sepolia.basescan.org" in adapter
    assert "switchInjectedWalletNetwork" in adapter
    assert "switchWalletToExpectedNetwork" in page
    assert "Base Sepolia" in page
    assert "Listo para volver a Telegram" in page
    assert "regresar a NODO" in page
    assert "Wallet lista en Base" not in page
    assert "eth_sendTransaction" not in adapter
    assert "eth_signTypedData" not in adapter
