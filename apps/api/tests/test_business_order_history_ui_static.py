from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_business_order_history_uses_cursor_pagination_and_neutral_empty_copy() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    api = _read("apps/web/src/api/businessOrders.ts")

    assert "BusinessOrdersPage" in model
    assert "BUSINESS_ORDER_PAGE_SIZE" in model
    assert "businessOrderNextCursor" in model
    assert "businessOrderLoadingMore" in model
    assert "loadMoreBusinessOrders" in model
    assert "append: true" in model
    assert "next_cursor" in model
    assert "cursor?: string" in api
    assert "params.set(\"cursor\", cursor)" in api

    assert "loadMoreBusinessOrders" in screen
    assert "businessOrderNextCursor" in screen
    assert "businessOrderLoadingMore" in screen
    assert "Cargar mas" in screen
    assert "No hay operaciones cerradas todavia." in screen
    assert "No hay ordenes completadas todavia." not in "\n".join((model, screen))
    assert 'businessOrderFilter === "history" ? businessOrders.length : historyCount' not in screen


def test_business_orders_nav_uses_cheap_history_fallback_only_when_open_is_empty() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    dashboard = _read("apps/web/src/screens/business-app/BusinessDashboardScreen.tsx")

    assert "openBusinessOrdersLanding" in model
    assert "fallbackToHistoryWhenEmpty" in model
    assert 'requestedStatus === "open"' in model
    assert 'listBusinessOrders<BusinessOrdersPage>(request, "history", null, BUSINESS_ORDER_PAGE_SIZE)' in model
    assert 'setBusinessOrderFilter("history")' in model
    assert "openBusinessOrdersLanding" in shell
    assert "void openBusinessOrdersLanding()" in shell
    assert "loadBusinessOrders(\"open\")" in dashboard
    assert "openBusinessOrdersLanding" not in dashboard
