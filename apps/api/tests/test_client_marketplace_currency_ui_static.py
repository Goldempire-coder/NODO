import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_client_marketplace_uses_one_method_aware_currency_presentation() -> None:
    payment_labels = _read("apps/web/src/constants/paymentLabels.ts")
    marketplace_screen = _read(
        "apps/web/src/screens/client/ClientMarketplaceScreens.tsx"
    )
    marketplace_card = _read(
        "apps/web/src/screens/client/marketplace/ClientMarketplaceAdCard.tsx"
    )
    currency_label = _read(
        "apps/web/src/screens/client/marketplace/ClientMarketplaceCurrencyLabel.tsx"
    )
    globals_css = _read("apps/web/src/app/globals.css")

    assert "paymentMethodCurrencyPresentation" in payment_labels
    assert 'currencyLabel: "USD"' in payment_labels
    assert 'currencyLabel: "USDT"' in payment_labels
    assert 'offerLabel: "Zelle · USD"' in payment_labels
    assert 'offerLabel: "USDT"' in payment_labels

    assert "ClientMarketplaceAdCard" in marketplace_screen
    assert "ClientMarketplaceAdCard" in marketplace_card
    assert "paymentMethodCurrencyPresentation(ad.payment_method)" in marketplace_card
    assert "presentation.offerLabel" in marketplace_card
    assert "ClientMarketplaceCurrencyLabel" in marketplace_card
    assert "presentation.currencyLabel" in currency_label
    assert "searchCurrency.amountSymbol" in marketplace_screen
    assert 'aria-label={`Monto en ${searchCurrency.currencyLabel}`}' in marketplace_screen

    for fixed_usd_copy in (
        'aria-label="Monto en USD"',
        "<strong>USD</strong>",
        "Bs / USD",
        "Bs/USD",
        "${ad.amount_min_usd}",
    ):
        assert fixed_usd_copy not in marketplace_screen
        assert fixed_usd_copy not in marketplace_card

    assert ".client-marketplace-currency--usd" in globals_css
    assert ".client-marketplace-currency--usdt" in globals_css
    assert "var(--nodo-success)" in globals_css
    assert "var(--nodo-text)" in globals_css


def test_client_marketplace_method_change_invalidates_old_results_and_filters_list() -> None:
    marketplace_model = _read(
        "apps/web/src/hooks/workspace/useClientMarketplaceModel.ts"
    )
    workspace_model = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")
    marketplace_screen = _read(
        "apps/web/src/screens/client/ClientMarketplaceScreens.tsx"
    )

    select_method = marketplace_model.split(
        "function selectMarketplacePaymentMethod", 1
    )[1].split("async function searchAds", 1)[0]
    active_list = marketplace_model.split(
        "async function loadActiveMarketplace", 1
    )[1].split("async function openAdDetail", 1)[0]

    assert "marketplaceRequestIdRef.current += 1" in select_method
    assert "adDetailRequestIdRef.current += 1" in select_method
    assert "setSearchResults([])" in select_method
    assert "setSelectedAd(null)" in select_method
    assert "setSearchingMarketplace(false)" in select_method
    assert "setLoadingMarketplace(false)" in select_method
    assert "payment_method: searchForm.payment_method" in active_list

    assert (
        "selectMarketplacePaymentMethod: marketplace.selectMarketplacePaymentMethod"
        in workspace_model
    )
    assert 'selectMarketplacePaymentMethod("zelle")' in marketplace_screen
    assert 'selectMarketplacePaymentMethod("usdt_trc20")' in marketplace_screen
    assert "payment_method: searchForm.payment_method" in marketplace_model


def test_client_order_flow_uses_method_aware_currency_presentation() -> None:
    order_screens = _read("apps/web/src/screens/client/ClientOrderScreens.tsx")
    payment_details = _read(
        "apps/web/src/screens/client/chat/ClientPaymentDetailsBubble.tsx"
    )

    assert "paymentMethodCurrencyPresentation" in order_screens
    assert re.search(
        r"paymentMethodCurrencyPresentation\(\s*selectedAd\?\.payment_method\s*\)",
        order_screens,
    )
    assert re.search(
        r"paymentMethodCurrencyPresentation\(\s*"
        r"selectedOrder\?\.payment_method_snapshot\s*\)",
        order_screens,
    )
    assert re.search(
        r"paymentMethodCurrencyPresentation\(\s*"
        r"order\.payment_method_snapshot\s*\)",
        order_screens,
    )
    assert "paymentMethodCurrencyPresentation" in payment_details
    assert re.search(
        r"paymentMethodCurrencyPresentation\(\s*methodType\s*\)",
        payment_details,
    )
    assert order_screens.count("{selectedAdCurrency.currencyLabel}") >= 2
    assert order_screens.count("{selectedOrderCurrency.currencyLabel}") >= 2
    assert "{orderCurrency.currencyLabel}" in order_screens
    assert "{currency.currencyLabel}" in payment_details

    for fixed_usd_copy in ("Bs/USD", "} USD"):
        assert fixed_usd_copy not in order_screens
        assert fixed_usd_copy not in payment_details
