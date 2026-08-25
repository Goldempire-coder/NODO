from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_business_credits_offers_metamask_probe_when_provider_is_missing() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")

    assert "Abrir MetaMask para probar conexión" in screen
    assert 'walletProviderStatus === "unavailable"' in screen
    assert "openMetaMaskWalletProbe" in model


def test_metamask_probe_uses_a_fixed_public_route_without_private_context() -> None:
    helper = _read("apps/web/src/lib/wallet/metamaskHandoff.ts")
    page = _read("apps/web/src/app/business/wallet-probe/page.tsx")

    assert 'const WALLET_PROBE_PATH = "/business/wallet-probe"' in helper
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
