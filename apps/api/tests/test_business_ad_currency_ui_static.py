from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_business_ad_amount_uses_one_method_aware_presenter() -> None:
    helpers = _read("apps/web/src/screens/business-app/ads/businessAdViewHelpers.ts")
    currency_label = _read("apps/web/src/screens/business-app/ads/BusinessAdCurrencyLabel.tsx")
    amount = _read("apps/web/src/screens/business-app/ads/BusinessAdAmount.tsx")
    card = _read("apps/web/src/screens/business-app/ads/BusinessAdCard.tsx")
    detail = _read("apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx")
    create_screen = _read("apps/web/src/screens/business-app/BusinessAdsScreens.tsx")

    assert 'zelle: { currencyLabel: "USD", currencyTone: "usd" }' in helpers
    assert 'usdt_trc20: { currencyLabel: "USDT", currencyTone: "usdt" }' in helpers
    assert "paymentMethods.find((method) => method.id === ad.payment_method_id)" in helpers
    assert "fromMethod?.receive_method" in helpers
    assert "adAmountCurrencyPresentation(methodType)" in helpers
    assert "adAmountPresentation(ad, paymentMethods)" in amount
    assert "BusinessAdCurrencyLabel" in currency_label
    assert "business-ad-currency--${presentation.currencyTone}" in currency_label
    assert "{presentation.currencyLabel}" in currency_label
    assert "<BusinessAdCurrencyLabel presentation={currencyPresentation} />" in amount
    assert "<BusinessAdAmount ad={ad} paymentMethods={paymentMethods} />" in card
    assert "<BusinessAdAmount ad={ad} paymentMethods={paymentMethods} />" in detail
    assert "adAmountCurrencyPresentation(adForm.payment_method)" in create_screen
    assert "displayUsdRange" not in "\n".join((helpers, currency_label, card, detail, create_screen))


def test_business_ad_create_and_edit_copy_uses_selected_method_currency() -> None:
    create_screen = _read("apps/web/src/screens/business-app/BusinessAdsScreens.tsx")
    card = _read("apps/web/src/screens/business-app/ads/BusinessAdCard.tsx")
    detail = _read("apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx")

    assert "Rango autorizado: {business?.min_order_amount_usd" in create_screen
    assert create_screen.count("<BusinessAdCurrencyLabel presentation={selectedCurrencyPresentation} />") >= 6
    assert "adAmountPresentation(ad, paymentMethods)" in card
    assert "adAmountPresentation(ad, paymentMethods)" in detail
    assert "{displayRate(ad)} / <BusinessAdCurrencyLabel presentation={currencyPresentation} />" in card
    assert "{displayRate(ad)} / <BusinessAdCurrencyLabel presentation={currencyPresentation} />" in detail
    assert detail.count("<BusinessAdCurrencyLabel presentation={editCurrencyPresentation} />") == 3
    assert "selectedCurrency =" not in create_screen
    assert "editCurrencyLabel" not in detail
    for source in (create_screen, detail):
        assert "Tasa Bs/USD" not in source
        assert "Min USD" not in source
        assert "Max USD" not in source
    assert "/ USD</span>" not in card
    assert "Recibiras {previewAmount} USD" not in create_screen


def test_business_ad_currency_labels_have_semantic_contrasting_styles() -> None:
    css = _read("apps/web/src/app/globals.css")

    assert ".business-ad-currency.business-ad-currency--usd" in css
    assert "color: var(--nodo-success)" in css
    assert ".business-ad-currency.business-ad-currency--usdt" in css
    assert "color: var(--nodo-text)" in css
