from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_business_order_history_uses_cursor_pagination_and_neutral_empty_copy() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    api = _read("apps/web/src/api/businessOrders.ts")

    assert "BusinessOrdersPage" in model
    assert "const BUSINESS_ORDER_PAGE_SIZE = 20;" in model
    assert "businessOrderNextCursor" in model
    assert "businessOrderLoadingMore" in model
    assert "loadMoreBusinessOrders" in model
    assert "append: true" in model
    assert "next_cursor" in model
    assert "limit = 20" in api
    assert "cursor?: string" in api
    assert "params.set(\"cursor\", cursor)" in api

    assert "loadMoreBusinessOrders" in screen
    assert "businessOrderNextCursor" in screen
    assert "businessOrderLoadingMore" in screen
    assert "Cargar mas" in screen
    assert "No hay operaciones cerradas todavia." in screen
    assert "Puedes revisar Por verificar o Historial cuando lo necesites." in screen
    assert "No hay ordenes completadas todavia." not in "\n".join((model, screen))
    assert 'businessOrderFilter === "history" ? businessOrders.length : historyCount' not in screen


def test_business_orders_nav_loads_open_only_and_never_falls_back_to_history() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    dashboard = _read("apps/web/src/screens/business-app/BusinessDashboardScreen.tsx")

    assert "openBusinessOrdersLanding" in model
    landing = model.split("const openBusinessOrdersLanding", 1)[1].split("const refreshBusinessOrderList", 1)[0]
    assert 'return loadBusinessOrders("open");' in landing
    assert '"history"' not in landing
    assert "fallbackToHistoryWhenEmpty" not in model
    assert "openBusinessOrdersLanding" in shell
    assert "void openBusinessOrdersLanding()" in shell
    assert "loadBusinessOrders(\"open\")" in dashboard
    assert "openBusinessOrdersLanding" not in dashboard


def test_business_order_tabs_track_loaded_filters_without_cross_filter_counts() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    screen = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")

    assert "loadedBusinessOrderFilters" in model
    assert "businessOrderFilterCounts" in model
    assert "markBusinessOrderFilterLoaded" in model
    assert "loadedBusinessOrderFilters.has" in screen
    assert "businessOrderFilterCounts[filter]" in screen
    assert "openTabCount" not in screen
    assert "verificationTabCount" not in screen
    assert "historyTabCount" not in screen
    assert 'loadBusinessOrders("payment_reported")' in screen
    assert 'loadBusinessOrders("history")' in screen


def test_business_order_tabs_use_compact_accessible_view_actions() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    css = _read("apps/web/src/app/globals.css")

    assert "BusinessOrderInboxTab" in screen
    assert 'ariaLabel="Ver órdenes abiertas"' in screen
    assert 'ariaLabel="Ver órdenes por verificar"' in screen
    assert 'ariaLabel="Ver historial de órdenes"' in screen
    assert 'className="business-order-tab__action"' in screen
    assert '<strong>{count}</strong>' in screen
    assert '<strong>{openTabCount || "Ver"}</strong>' not in screen
    assert ".business-order-tab__action" in css
    assert ".business-priority-list button:focus-visible" in css


def test_business_order_filter_requests_keep_late_response_guard() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")

    assert "businessOrderListRequestIdRef" in model
    assert "businessOrderListRequestIdRef.current !== targetListRequestId" in model
    assert "businessOrderFilterRef.current !== status" in model


def test_business_order_detail_shows_loading_state_before_detail_arrives() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")

    detail_screen = screen.split("export function BusinessOrderDetailScreen", 1)[1]
    assert "businessOrderDetail ? (" in detail_screen
    assert "busy ? (" in detail_screen
    assert "Cargando orden..." in detail_screen
    assert 'role="status"' in detail_screen
    assert "Selecciona una orden para ver el detalle." in detail_screen


def test_business_confirm_payment_uses_pin_gate_in_detail_and_chat() -> None:
    route = _read("apps/api/app/modules/orders/business_routes.py")
    orders_model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    chat_actions = _read("apps/web/src/hooks/business-mini-app/chat/useBusinessChatOrderActions.ts")
    pin_screen = _read("apps/web/src/screens/business-app/BusinessPinScreen.tsx")

    confirm_route = route.split("def confirm_business_payment", 1)[1].split("@router.post", 1)[0]
    assert "_require_business_pin(request, user)" in confirm_route
    assert '"confirm-payment" | "cannot-attend"' in orders_model
    assert 'businessOrderPinActionLabel(action)' in orders_model
    assert 'queuePendingBusinessOrderPinAction({ orderId: targetOrderId, action })' in orders_model
    assert 'data.order.capabilities.can_confirm_payment' in orders_model
    assert '(action === "confirm-payment" || action === "mark-delivered")' in chat_actions
    assert "routeBusinessPinError({ action: actionLabel, error, setNotice, setView })" in chat_actions
    assert "PIN para confirmar pago" in pin_screen
    assert "Activar PIN y confirmar" in pin_screen
