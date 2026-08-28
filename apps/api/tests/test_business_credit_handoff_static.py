from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_credit_handoff_puts_token_in_static_safe_metamask_path_and_clears_url() -> None:
    helper = _read("apps/web/src/lib/wallet/metamaskHandoff.ts")
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")
    page_state = _read("apps/web/src/app/business/credit-payment/creditPaymentHandoffPageState.ts")
    redirects = _read("apps/web/public/_redirects")

    assert 'const CREDIT_PAYMENT_HANDOFF_PATH_PREFIX = "/business/credit-payment/handoff/"' in helper
    assert 'new URL(`${CREDIT_PAYMENT_HANDOFF_PATH_PREFIX}${handoffToken}/`, source.origin)' in helper
    assert "dappUrl = `${target.host}${target.pathname}`" in helper
    assert 'target.searchParams.set("handoff", handoffToken)' not in helper
    assert "encodeURIComponent(target.search)" not in helper
    assert "dappUrl = `${target.host}${target.pathname}${target.search}`" not in helper
    assert "target.hash" not in helper
    assert "%23" not in helper
    assert "encodeURIComponent(dappUrl)" not in helper
    assert "`${METAMASK_DAPP_DEEPLINK_BASE}${dappUrl}`" in helper

    assert "/business/credit-payment/handoff/:token/ /business/credit-payment/ 200" in redirects
    assert "/business/credit-payment/handoff/:token /business/credit-payment/ 200" in redirects

    assert "extractCreditHandoffToken" in page
    assert "extractCreditHandoffToken(window.location.search, window.location.hash, window.location.pathname, window.history.state)" in page
    assert 'const pathMatch = pathname.match(/^\\/business\\/credit-payment\\/handoff\\/([A-Za-z0-9_-]{43})\\/?$/)' in page_state
    assert "readHandoffTokenFromHistoryState(historyState)" in page_state
    assert "nodoCreditHandoffToken" in page_state
    assert "new URLSearchParams(search).get(\"handoff\")" in page_state
    assert "new URLSearchParams(fragment.replace(/^#/, \"\")).get(\"handoff\")" in page_state
    assert "window.history.replaceState" in page
    assert "window.history.replaceState({ nodoCreditHandoffToken: token }, \"\", \"/business/credit-payment/\")" in page
    assert "window.history.replaceState(null, \"\", `${window.location.pathname}${window.location.search}`)" not in page
    effect = page.split("useEffect(() => {", 1)[1].split("}, []);", 1)[0]
    assert effect.index("window.history.replaceState") < effect.index("getCreditHandoffChallenge")
    assert "localStorage" not in page
    assert "sessionStorage" not in page


def test_credit_handoff_dead_end_errors_offer_one_telegram_exit_without_wallet_actions() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")
    page_state = _read("apps/web/src/app/business/credit-payment/creditPaymentHandoffPageState.ts")

    assert "function returnToTelegram()" in page_state
    assert 'window.location.assign("tg://")' in page_state
    assert "Este enlace no es valido. Vuelve a Telegram para iniciar de nuevo." in page
    assert "Volver a Telegram" in page

    dead_end_branch = page.split(") : !paymentDetail && !loadingChallenge && !challenge ? (", 1)[1].split(
        ") : !paymentDetail && (loadingChallenge || challenge)",
        1,
    )[0]
    assert dead_end_branch.count("<button") == 1
    assert "Volver a Telegram" in dead_end_branch
    assert "connectWallet" not in dead_end_branch
    assert "switchWalletToExpectedNetwork" not in dead_end_branch
    assert "confirmWallet" not in dead_end_branch
    assert "approveTestUsdc" not in dead_end_branch
    assert "submitTestPayment" not in dead_end_branch


def test_credit_handoff_wallet_confirmation_error_exits_to_telegram_without_wallet_retry() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")
    page_state = _read("apps/web/src/app/business/credit-payment/creditPaymentHandoffPageState.ts")

    assert "function isWalletUserRejected(error: unknown)" in page_state
    assert "walletConfirmationRequiresTelegramRestart" in page
    assert "setWalletConfirmationRequiresTelegramRestart(!isWalletUserRejected(error))" in page

    confirmation_error_branch = page.split(
        "{!paymentDetail && walletConfirmationRequiresTelegramRestart ? (",
        1,
    )[1].split(
        ") : !paymentDetail && !loadingChallenge && !challenge",
        1,
    )[0]
    assert confirmation_error_branch.count("<button") == 1
    assert "Volver a Telegram" in confirmation_error_branch
    assert "connectWallet" not in confirmation_error_branch
    assert "switchWalletToExpectedNetwork" not in confirmation_error_branch
    assert "confirmWallet" not in confirmation_error_branch
    assert "approveTestUsdc" not in confirmation_error_branch
    assert "submitTestPayment" not in confirmation_error_branch


def test_credit_handoff_page_does_not_offer_wallet_actions_without_valid_challenge() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")

    wallet_label_branch = page.split('loadingChallenge\n                    ? "Validando enlace"', 1)[1].split(
        ": walletProviderStatus",
        1,
    )[0]
    assert "connectedWalletAddress" in wallet_label_branch
    assert '"Wallet conectada"' in wallet_label_branch
    assert "connectedWalletAddress && challenge" in page
    assert "!paymentDetail && (loadingChallenge || challenge)" in page


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
            _read("apps/web/src/app/business/credit-payment/creditPaymentHandoffPageState.ts"),
            _read("apps/web/src/lib/wallet/metamaskHandoff.ts"),
            _read("apps/web/src/lib/wallet/eip1193.ts"),
            _read("apps/web/src/lib/wallet/testnetCreditPayment.ts"),
            _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts"),
        )
    ).lower()

    payment_helper = _read("apps/web/src/lib/wallet/testnetCreditPayment.ts")
    payment_page = _read("apps/web/src/app/business/credit-payment/page.tsx")
    payment_page_state = _read("apps/web/src/app/business/credit-payment/creditPaymentHandoffPageState.ts")
    payment_runtime = f"{payment_page}\n{payment_page_state}"

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
    assert "Pago enviado" in payment_runtime
    assert "Volver a NODO" in payment_page
    assert "Pago enviado. Vuelve a Telegram y toca Actualizar" not in payment_runtime

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


def test_credit_payment_skips_manual_permission_recheck_after_exact_approval() -> None:
    page = _read("apps/web/src/app/business/credit-payment/page.tsx")

    assert '"review"' in page
    assert '"approval_submitted"' not in page
    assert "checkTestUsdcPermission" in page
    assert "setPaymentStep(\"review\")" in page
    assert "Revisar permiso de USDC" in page
    assert "Ya autorice USDC, revisar permiso" not in page

    approve_block = page.split("const approveTestUsdc = async", 1)[1].split(
        "const submitTestPayment = async",
        1,
    )[0]
    assert 'setPaymentStep("pay")' in approve_block


def test_telegram_credit_flow_creates_handoff_and_refreshes_automatically() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    presentation = _read("apps/web/src/screens/business-app/businessCreditPresentation.ts")

    assert "createBusinessCreditHandoff" in model
    assert "openMetaMaskCreditHandoff" in model
    assert "refreshCreditHandoff" in model
    assert "Abrir MetaMask" in screen
    assert "NODO esta revisando el pago automaticamente." in screen
    assert "AUTO_REFRESH_PENDING_CREDIT_PAYMENT_LIMIT = 18" in presentation
    assert "refreshSelectedCreditPurchase({ silent: true })" in screen
    assert "pulsa Actualizar" not in model
    assert "Actualiza el estado" not in model
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


def test_business_credit_success_state_uses_clear_business_copy_without_contract_debug() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert 'selectedCreditPurchase?.status === "credited"' in screen
    assert "Pago exitoso" in screen
    assert "Se acreditaron" in screen
    assert "Ver mis creditos" in screen
    assert "loadCreditDashboard" in screen

    success_branch = screen.split('selectedCreditPurchase?.status === "credited"', 1)[1].split(
        "const statusCopy",
        1,
    )[0]
    assert "Contrato:" not in success_branch
    assert "Version:" not in success_branch
    assert "Autorizacion:" not in success_branch
    assert "Puede pagar:" not in success_branch


def test_business_credit_pending_screen_auto_refreshes_visible_purchase_without_interval() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")

    assert "AUTO_REFRESH_CREDIT_HANDOFF_MS" in screen
    assert "AUTO_REFRESH_CREDIT_HANDOFF_LIMIT" in screen
    assert "AUTO_REFRESH_PENDING_CREDIT_PAYMENT_MS" in screen
    assert "AUTO_REFRESH_PENDING_CREDIT_PAYMENT_LIMIT" in screen
    assert "window.setTimeout" in screen
    assert "window.clearTimeout" in screen
    assert "setInterval(" not in screen
    assert "silent?: boolean" in model
    assert "Estado de compra actualizado." in model
    assert "Pago exitoso. Tus creditos ya estan disponibles." in model

    launch_branch = model.split("const openMetaMaskCreditHandoff = useCallback", 1)[1].split(
        "await prepareMetaMaskCreditHandoff();",
        1,
    )[0]
    assert "launchMetaMaskCreditHandoff(creditHandoffLaunchToken)" in launch_branch
    before_launch = launch_branch.split("launchMetaMaskCreditHandoff", 1)[0]
    assert "await " not in before_launch

    assert "creditHandoffLaunchReady" in screen
    assert "Preparando enlace..." in screen
    assert "Enlace listo - Abrir MetaMask" in screen


def test_telegram_handoff_prepares_default_starter_only_from_visible_buy_screen() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    rules = _read("apps/web/src/hooks/business-mini-app/businessCreditPaymentRules.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert 'DEFAULT_CREDIT_PACKAGE = "starter"' in rules
    assert 'setCreditPackage((current) => current || DEFAULT_CREDIT_PACKAGE)' in model
    assert "prepareMetaMaskCreditHandoff({ silent: true })" not in model
    assert "prepareMetaMaskCreditHandoff({ silent: true })" in screen
    assert "canPrepareCreditHandoffSilently" in screen
    assert "canPrepareCreditHandoffSilently" in model
    assert "accessLink.pin_unlocked" in model
    assert "accessLink?.pin_required" in model


def test_credit_payment_silent_auto_refresh_does_not_surface_manual_loading_state() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    refresh_block = model.split(
        "const refreshSelectedCreditPurchase = useCallback",
        1,
    )[1].split("const loadReferrals", 1)[0]

    assert "const showManualRefreshLoading = !silent" in refresh_block
    assert "refreshingCreditPurchaseRef.current" in refresh_block
    assert "if (showManualRefreshLoading) {" in refresh_block
    assert "setRefreshingCreditPurchase(true)" in refresh_block
    assert "setRefreshingCreditPurchase(false)" in refresh_block
    assert "refreshSelectedCreditPurchase({ silent: true })" in screen
    pending_screen = screen.split("export function CreditPaymentPendingScreen", 1)[1].split(
        "export function ReferralProgramScreen",
        1,
    )[0]
    assert "Actualizar estado" not in pending_screen
    assert "Actualizando..." not in pending_screen


def test_pending_credit_payment_waits_for_auto_accreditation_without_user_refresh_cta() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    presentation = _read("apps/web/src/screens/business-app/businessCreditPresentation.ts")
    handoff_page_state = _read("apps/web/src/app/business/credit-payment/creditPaymentHandoffPageState.ts")

    pending_screen = screen.split("export function CreditPaymentPendingScreen", 1)[1].split(
        "export function ReferralProgramScreen",
        1,
    )[0]
    assert "Estamos acreditando" in presentation
    assert "menos de un minuto" in presentation
    assert "Esta pantalla se actualiza sola" in presentation
    assert "se acreditan automaticamente" in handoff_page_state
    assert "refreshSelectedCreditPurchase({ silent: true })" in pending_screen
    assert "Preparar nueva compra" in pending_screen
    assert "Actualizar estado" not in pending_screen
    assert "Actualizando..." not in pending_screen


def test_pending_credit_purchase_hides_package_picker_and_uses_one_primary_path() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")

    assert 'pendingCreditPurchase ? "Continua tu pago" : "Elige un paquete"' in screen
    assert '!pendingCreditPurchase ? (\n        <div className="credit-package-grid">' in screen
    assert "!pendingCreditPurchase ? (\n        <div className=\"business-status-panel\">" in screen
    assert "pendingSelected" in screen
    assert "displayedSelection" in screen

    pending_branch = screen.split("{pendingCreditPurchase ? (", 1)[1].split(
        ") : loadingPendingPurchase ? (",
        1,
    )[0]
    assert "credit-package-grid" not in pending_branch


def test_contract_pending_dismiss_is_backend_owned_and_watcher_safe() -> None:
    routes = _read("apps/api/app/modules/credits/routes.py")
    schemas = _read("apps/api/app/modules/credits/schemas.py")
    service = _read("apps/api/app/modules/credits/business_purchases.py")
    postgres_contract = _read("apps/api/app/modules/credits/postgres_contract_purchase.py")
    postgres_onchain = _read("apps/api/app/modules/credits/postgres_onchain.py")

    assert '@router.post("/business/credits/purchases/{purchase_id}/dismiss")' in routes
    assert "ContractCreditPurchaseDismissRequest" in schemas
    assert 'confirmation: str = Field(pattern="^NO_PAYMENT_SENT$")' in schemas
    assert "crypto_contract_credit_purchase_dismissed" in service
    assert "owner_dismissed_at = now()" in postgres_contract
    assert "owner_dismissed_by_user_id = %s" in postgres_contract
    assert "CRYPTO_PAYMENT_DISMISS_NOT_ALLOWED" in postgres_contract
    assert "status <> 'pending_payment'" in postgres_contract
    assert "owner_dismissed_at is null" in postgres_contract

    migration_up = _read("database/migrations/0060_contract_credit_purchase_owner_dismiss.up.sql")
    migration_down = _read("database/migrations/0060_contract_credit_purchase_owner_dismiss.down.sql")
    assert "add column if not exists owner_dismissed_at" in migration_up
    assert "references users(id) on delete set null" in migration_up
    assert "credit_purchases_contract_owner_dismissed_idx" in migration_up
    assert "0060 rollback blocked: owner dismissed contract purchases exist" in migration_down
    assert "drop column if exists owner_dismissed_at" in migration_down

    watcher_selection = postgres_onchain.split("def list_contract_pending_purchases_pg", 1)[1].split(
        "def _mark_detected",
        1,
    )[0]
    assert "owner_dismissed_at" not in watcher_selection


def test_telegram_pending_payment_uses_single_primary_cta_with_discrete_dismiss() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    rules = _read("apps/web/src/hooks/business-mini-app/businessCreditPaymentRules.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    api = _read("apps/web/src/api/credits.ts")
    styles = _read("apps/web/src/app/globals.css")

    assert "dismissBusinessContractCreditPurchase" in api
    assert 'confirmation: "NO_PAYMENT_SENT"' in api
    assert "pendingDismissConfirmationRequested" in model
    assert "dismissPendingBaseUsdcPayment" in model
    assert "requestPendingCreditPurchaseDismiss" in model
    assert "resetPendingCreditPurchaseDismiss" in model
    assert "owner_dismissed" in rules
    assert "Confirmar descarte" in screen
    assert "No envie el pago" in screen
    assert "Mantener pago pendiente" in screen
    assert "mini-inline-action" in screen
    assert ".mini-inline-action" in styles
    assert "cancelar pago" not in screen.lower()
    assert "creditHandoffLaunchToken" in model
    assert "pendingCreditPurchase" in model


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


def test_telegram_handoff_resumes_backend_pending_purchase_with_new_link() -> None:
    api = _read("apps/web/src/api/credits.ts")
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    routes = _read("apps/api/app/modules/credits/routes.py")

    assert "getBusinessPendingContractCreditPurchase" in api
    assert "/api/v1/business/credits/purchases/pending-contract" in api
    assert "loadBackendPendingBaseUsdcPurchase" in model
    assert "await loadBackendPendingBaseUsdcPurchase()" in model
    assert "Tienes un pago Base USDC pendiente. Continua ese pago antes de abrir otro." in model
    assert "createBusinessCreditHandoff(request, data.purchase.package_code)" in model
    assert "Enlace listo. Toca Continuar en MetaMask para terminar el pago pendiente." in model
    continue_branch = model.split("const continuePendingBaseUsdcPayment = useCallback", 1)[1].split(
        "const loadCreditDashboard = useCallback",
        1,
    )[0]
    assert "launchMetaMaskCreditHandoff(creditHandoffLaunchToken)" in continue_branch
    assert "await " not in continue_branch.split("launchMetaMaskCreditHandoff", 1)[0]
    assert "Boolean(pendingCreditPurchase)" not in screen
    assert "pendingCreditPurchase && pendingDismissConfirmationRequested" in screen
    assert "continuePendingBaseUsdcPayment()" in screen
    assert "openMetaMaskCreditHandoff()" in screen
    assert screen.count("continuePendingBaseUsdcPayment()") == 1
    assert "Continuar pago pendiente" in screen
    assert "Enlace listo - Continuar en MetaMask" in screen
    assert '@router.get("/business/credits/purchases/pending-contract")' in routes
    assert routes.index('@router.get("/business/credits/purchases/pending-contract")') < routes.index(
        '@router.get("/business/credits/purchases/{purchase_id}")'
    )


def test_postgres_pending_contract_purchase_reader_filters_business_and_expiry() -> None:
    postgres = _read("apps/api/app/modules/credits/postgres_contract_purchase.py")
    repository = _read("apps/api/app/modules/credits/postgres_repository.py")

    assert "def find_pending_contract_purchase_pg" in postgres
    assert "business_id = %s" in postgres
    assert "payment_method = 'base_usdc_contract'" in postgres
    assert "'pending_payment'" in postgres
    assert "'pending_onchain_confirmation'" in postgres
    assert "'detected'" in postgres
    assert "'under_review'" in postgres
    assert "payment_authorization_expires_at" in postgres
    assert "order by created_at asc" in postgres
    assert "find_pending_contract_purchase_pg" in repository


def test_business_credit_screen_mirrors_fractional_testnet_contract_prices() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    presentation = _read("apps/web/src/screens/business-app/businessCreditPresentation.ts")

    assert "BASE_CREDIT_PACKAGES" in presentation
    assert "TESTNET_CREDIT_PACKAGE_PRICE_SCALE = 0.01" in presentation
    assert 'new Set(["local", "test", "staging"])' in presentation
    assert "getPublicEnv().NEXT_PUBLIC_APP_ENV" in presentation
    assert "contractCreditPackagesForCurrentEnv" in screen
    assert "formatContractTestnetPrice" in presentation
    assert "{CREDIT_PACKAGES.map" not in screen
