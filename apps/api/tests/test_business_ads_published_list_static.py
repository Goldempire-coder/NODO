from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_published_ads_screen_keeps_all_ad_details_visible() -> None:
    ads_screen = _read("apps/web/src/screens/business-app/BusinessAdsScreens.tsx")
    detail_panel = _read("apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx")
    globals_css = _read("apps/web/src/app/globals.css")

    my_ads_block = ads_screen.split("export function MyAdsScreen", 1)[1].split("export function ArchivedAdsScreen", 1)[0]

    assert "business-list--published-ads" in my_ads_block
    assert 'ownAds.map((ad) => (' in my_ads_block
    assert '<BusinessAdDetailPanel ad={ad} key={ad.id} mode="list" model={model} />' in my_ads_block
    assert "selectedAd ?" not in my_ads_block
    assert "isEditingSelectedAd && selectedAdId === ad.id" in detail_panel
    assert "business-ad-detail--list-item" in detail_panel
    assert ".business-list--published-ads" in globals_css
    assert "max-height: none;" in globals_css
    assert "overflow: visible;" in globals_css
