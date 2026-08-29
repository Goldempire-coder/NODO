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
    assert "ownAdsNextCursor" in my_ads_block
    assert "loadMoreOwnAds" in my_ads_block
    assert "ownAdsLoadingMore" in my_ads_block
    assert "Cargar mas anuncios" in my_ads_block
    assert "selectedAd ?" not in my_ads_block
    assert "isEditingSelectedAd && selectedAdId === ad.id" in detail_panel
    assert "business-ad-detail--list-item" in detail_panel
    assert ".business-list--published-ads" in globals_css
    assert "max-height: none;" in globals_css
    assert "overflow: visible;" in globals_css


def test_business_ads_model_uses_backend_cursor_for_incremental_published_ads() -> None:
    ads_model = _read("apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts")
    ads_api = _read("apps/web/src/api/businessAds.ts")

    assert "BUSINESS_AD_PAGE_SIZE = 20" in ads_model
    assert "type BusinessAdsPage" in ads_model
    assert "ownAdsNextCursor" in ads_model
    assert "ownAdsLoadingMore" in ads_model
    assert "loadMoreOwnAds" in ads_model
    assert "setOwnAdsNextCursor(data.next_cursor ?? null)" in ads_model
    assert "const knownIds = new Set(current.map((item) => item.id));" in ads_model
    assert "listBusinessAds<BusinessAdsPage>(request, BUSINESS_AD_PAGE_SIZE, cursor)" in ads_model
    assert "loadMoreOwnAds," in ads_model
    assert "ownAdsNextCursor," in ads_model
    assert "ownAdsLoadingMore," in ads_model

    assert "cursor?: string | null" in ads_api
    assert "searchParams.set(\"cursor\", cursor)" in ads_api


def test_business_ads_screens_show_loading_without_false_empty_copy() -> None:
    ads_screen = _read("apps/web/src/screens/business-app/BusinessAdsScreens.tsx")

    my_ads_block = ads_screen.split("export function MyAdsScreen", 1)[1].split("export function ArchivedAdsScreen", 1)[0]
    archived_block = ads_screen.split("export function ArchivedAdsScreen", 1)[1].split("export function PaymentMethodsScreen", 1)[0]

    assert "loadingScreen" in my_ads_block
    assert 'loadingScreen === "my-ads"' in my_ads_block
    assert "Cargando anuncios..." in my_ads_block
    assert "!isLoadingOwnAds && ownAds.length === 0" in my_ads_block

    assert "loadingScreen" in archived_block
    assert 'loadingScreen === "archived-ads"' in archived_block
    assert "Cargando archivados..." in archived_block
    assert "!isLoadingArchivedAds && archivedAds.length === 0" in archived_block


def test_archived_ads_use_backend_cursor_pagination() -> None:
    ads_model = _read("apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts")
    ads_api = _read("apps/web/src/api/businessAds.ts")
    ads_screen = _read("apps/web/src/screens/business-app/BusinessAdsScreens.tsx")

    assert "archivedAdsNextCursor" in ads_model
    assert "archivedAdsLoadingMore" in ads_model
    assert "archivedAdsRequestIdRef" in ads_model
    assert "loadMoreArchivedAds" in ads_model
    assert "setArchivedAdsNextCursor(data.next_cursor ?? null)" in ads_model
    assert "listArchivedBusinessAds<BusinessAdsPage>(request, BUSINESS_AD_PAGE_SIZE, cursor)" in ads_model

    assert "listArchivedBusinessAds<T>(request: AuthenticatedRequest, limit = 20, cursor?: string | null)" in ads_api
    assert 'request<T>(`/api/v1/business/ads/archived?${searchParams.toString()}`)' in ads_api

    archived_block = ads_screen.split("export function ArchivedAdsScreen", 1)[1].split("export function PaymentMethodsScreen", 1)[0]
    assert "archivedAdsNextCursor" in archived_block
    assert "archivedAdsLoadingMore" in archived_block
    assert "loadMoreArchivedAds" in archived_block
    assert "Cargar mas archivados" in archived_block
