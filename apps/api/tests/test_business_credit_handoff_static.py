from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_credit_handoff_uses_fragment_and_clears_it_before_network_work() -> None:
    helper = _read("apps/web/src/lib/wallet/metamaskHandoff.ts")
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")

    assert 'const CREDIT_PAYMENT_PATH = "/business/credit-payment"' in helper
    assert "target.hash = `handoff=${handoffToken}`" in helper
    assert "extractCreditHandoffToken" in page
    assert "window.history.replaceState" in page
    effect = page.split("useEffect(() => {", 1)[1].split("}, []);", 1)[0]
    assert effect.index("window.history.replaceState") < effect.index("getCreditHandoffChallenge")
    assert "localStorage" not in page
    assert "sessionStorage" not in page


def test_credit_handoff_page_signs_only_the_backend_challenge() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")
    wallet = _read("apps/web/src/lib/wallet/eip1193.ts")
    api = _read("apps/web/src/api/credits.ts")

    assert "signWalletChallenge" in page
    assert 'method: "personal_sign"' in wallet
    assert "claimCreditHandoff" in page
    assert 'credentials: "omit"' in api
    public_api = api.split("async function publicCreditHandoffRequest", 1)[1]
    assert "Authorization" not in public_api


def test_credit_handoff_runtime_contains_no_payment_or_auth_transfer() -> None:
    source = "\n".join(
        (
            _read("apps/web/src/app/business/credit-payment/page.tsx"),
            _read("apps/web/src/lib/wallet/metamaskHandoff.ts"),
            _read("apps/web/src/lib/wallet/eip1193.ts"),
            _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts"),
        )
    ).lower()

    for forbidden in (
        "eth_sendtransaction",
        "eth_signtypeddata",
        "tx_hash",
        "approve(",
        "pay(",
        "accesstoken",
        "refreshtoken",
        "initdata",
        "document.cookie",
        "setinterval(",
        "@reown/",
        "@walletconnect/",
        'from "wagmi"',
        'from "viem"',
    ):
        assert forbidden not in source


def test_telegram_credit_flow_creates_handoff_and_refreshes_manually() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert "createBusinessCreditHandoff" in model
    assert "openMetaMaskCreditHandoff" in model
    assert "refreshCreditHandoff" in model
    assert "Abrir MetaMask" in screen
    assert "Actualizar" in screen
    assert "setInterval(" not in model


def test_telegram_handoff_launch_waits_for_a_direct_second_tap() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert "creditHandoffLaunchReady" in screen
    assert "Preparar enlace MetaMask" in screen
    assert "Enlace listo. Toca Abrir MetaMask" in model

    creation_branch = model.split("const data = await createBusinessCreditHandoff", 1)[1].split("} catch", 1)[0]
    assert "setCreditHandoffLaunchToken(data.handoff.token)" in creation_branch
    assert "launchMetaMaskCreditHandoff" not in creation_branch

    launch_branch = model.split("if (creditHandoffLaunchToken) {", 1)[1].split("const action =", 1)[0]
    assert "launchMetaMaskCreditHandoff(creditHandoffLaunchToken)" in launch_branch
