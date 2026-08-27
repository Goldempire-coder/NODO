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


def test_credit_handoff_uses_backend_network_profile_for_wallet_validation() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")
    types = _read("apps/web/src/types/credits.ts")

    assert "challenge.network" in page
    assert "challenge.chain_id" in page
    assert "data.is_testnet" in page
    assert "expectedNetwork" in page
    assert "Base Sepolia" in page
    handoff_type = types.split("export type CreditHandoff = {", 1)[1].split("};", 1)[0]
    challenge_type = types.split("export type CreditHandoffChallenge = {", 1)[1].split("};", 1)[0]
    assert "network: CreditPaymentNetwork;" in handoff_type
    assert "network: CreditPaymentNetwork;" in challenge_type
    assert "network: string" not in handoff_type
    assert "network: string" not in challenge_type
    assert "is_testnet: boolean" in types


def test_credit_handoff_runtime_contains_testnet_payment_without_auth_transfer() -> None:
    source = "\n".join(
        (
            _read("apps/web/src/app/business/credit-payment/page.tsx"),
            _read("apps/web/src/lib/wallet/metamaskHandoff.ts"),
            _read("apps/web/src/lib/wallet/eip1193.ts"),
            _read("apps/web/src/lib/wallet/testnetCreditPayment.ts"),
            _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts"),
        )
    ).lower()

    payment_helper = _read("apps/web/src/lib/wallet/testnetCreditPayment.ts")
    payment_page = _read("apps/web/src/app/business/credit-payment/page.tsx")

    assert 'method: "eth_call"' in payment_helper
    assert 'method: "eth_sendtransaction"' in payment_helper.lower()
    assert 'const erc20_approve_selector = "095ea7b3"' in payment_helper.lower()
    assert 'const vault_pay_selector = "a1147e9b"' in payment_helper.lower()
    approve_call = payment_helper.split("export async function approveExactTestUsdc", 1)[1].split(
        "export async function payTestCreditPurchase", 1
    )[0]
    pay_encoding = payment_helper.split("export function encodeTestCreditPaymentCall", 1)[1].split(
        "export async function payTestCreditPurchase", 1
    )[0]
    assert "wordFromUint(snapshot.amount)" in approve_call
    assert "snapshot.purchaseRef" in pay_encoding
    assert "snapshot.signature" in pay_encoding
    assert "snapshot.amount" in pay_encoding
    assert "expected_amount_units" in payment_helper
    assert "authorization_signature" in payment_helper
    assert "paymentauthorizationexpired" in payment_helper.lower()
    assert "Autorizar USDC de prueba" in payment_page
    assert "Pagar creditos de prueba" in payment_page
    assert "Pago enviado. Vuelve a Telegram y toca Actualizar" in payment_page

    for forbidden in (
        "eth_signtypeddata",
        "tx_hash",
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

    assert "setinterval(" not in payment_helper.lower()
    assert "settimeout(" not in payment_helper.lower()


def test_credit_payment_invalidates_authorization_on_wallet_or_network_change() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")

    wallet_change_handler = page.split("useInjectedWallet(() => {", 1)[1].split("}, expectedNetwork)", 1)[0]
    assert "setPaymentDetail(null)" in wallet_change_handler
    assert "setPaymentStep" in wallet_change_handler
    assert "La cuenta o red cambio" in wallet_change_handler


def test_credit_payment_keeps_recoverable_permission_steps() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")

    assert '"review"' in page
    assert '"approval_submitted"' in page
    assert "checkTestUsdcPermission" in page
    assert "setPaymentStep(\"review\")" in page
    assert "Revisar permiso de USDC" in page
    assert "Ya autorice USDC, revisar permiso" in page

    approve_block = page.split("const approveTestUsdc = async", 1)[1].split(
        "const submitTestPayment = async",
        1,
    )[0]
    assert 'setPaymentStep("pay")' not in approve_block
    assert 'setPaymentStep("approval_submitted")' in approve_block


def test_telegram_credit_flow_creates_handoff_and_refreshes_manually() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert "createBusinessCreditHandoff" in model
    assert "openMetaMaskCreditHandoff" in model
    assert "refreshCreditHandoff" in model
    assert "Abrir MetaMask" in screen
    assert "Actualizar" in screen
    assert "setInterval(" not in model


def test_telegram_handoff_exposes_one_payment_cta_with_safe_retry() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert "Abrir MetaMask para pagar en prueba" in screen
    assert "Preparar enlace MetaMask" not in screen
    assert "void connectWallet()" not in screen
    assert "Preparar autorizacion" not in screen

    creation_branch = model.split("const data = await createBusinessCreditHandoff", 1)[1].split("} catch", 1)[0]
    assert "setCreditHandoffLaunchToken(data.handoff.token)" in creation_branch
    assert "launchMetaMaskCreditHandoff(data.handoff.token)" not in creation_branch
    assert "Enlace listo. Toca Abrir MetaMask para continuar." in creation_branch

    launch_branch = model.split("if (creditHandoffLaunchToken) {", 1)[1].split("const action =", 1)[0]
    assert "launchMetaMaskCreditHandoff(creditHandoffLaunchToken)" in launch_branch
    before_launch = launch_branch.split("launchMetaMaskCreditHandoff", 1)[0]
    assert "await " not in before_launch

    assert "creditHandoffLaunchReady" in screen
    assert "Preparando enlace..." in screen
    assert "Enlace listo - Abrir MetaMask" in screen


def test_telegram_handoff_shows_rate_limit_next_to_the_cta_without_false_success() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert 'error.code === "RATE_LIMITED"' in model
    assert "Demasiados intentos. Espera unos minutos y vuelve a intentar." in model
    assert "setCreditHandoffError" in model
    assert "creditHandoffError" in screen
    assert 'role="alert"' in screen
    assert "Intentamos abrir MetaMask" in model
    assert "Intentamos abrir MetaMask" in screen
    assert "Pago de prueba abierto en MetaMask" not in screen


def test_business_credit_screen_mirrors_fractional_testnet_contract_prices() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert "BASE_CREDIT_PACKAGES" in screen
    assert "TESTNET_CREDIT_PACKAGE_PRICE_SCALE = 0.01" in screen
    assert 'new Set(["local", "test", "staging"])' in screen
    assert "getPublicEnv().NEXT_PUBLIC_APP_ENV" in screen
    assert "contractCreditPackagesForCurrentEnv" in screen
    assert "formatContractTestnetPrice" in screen
    assert "{CREDIT_PACKAGES.map" not in screen
