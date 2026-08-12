from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_critical_lists_use_cursor_pagination_without_stale_replacement() -> None:
    orders = _read("apps/web/src/hooks/admin-web/useAdminOrdersModel.ts")
    disputes = _read("apps/web/src/hooks/admin-web/useAdminDisputesModel.ts")
    support = _read("apps/web/src/hooks/admin-web/useAdminSupportModel.ts")
    helpers = _read("apps/web/src/hooks/pagination.ts")
    order_dispute_screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")
    support_screen = _read("apps/web/src/screens/admin-web/AdminSupportScreens.tsx")

    for source in (orders, disputes, support):
        assert "next_cursor" in source
        assert "RequestEpoch" in source or "requestEpoch" in source
        assert "appendUniqueById" in source

    assert "knownIds" in helpers

    assert "loadMoreOrders" in orders
    assert "loadMoreDisputes" in disputes
    assert "loadMoreSupportTickets" in support
    assert order_dispute_screen.count("Cargar mas") >= 2
    assert "loadMoreOrders" in order_dispute_screen
    assert "loadMoreDisputes" in order_dispute_screen
    assert "loadMoreSupportTickets" in support_screen
    assert "Cargar mas" in support_screen


def test_client_orders_and_surface_support_use_explicit_cursor_pagination() -> None:
    orders_api = _read("apps/web/src/api/orders.ts")
    orders_model = _read("apps/web/src/hooks/workspace/useRemitterOrdersModel.ts")
    client_model = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")
    order_screen = _read("apps/web/src/screens/client/ClientOrderScreens.tsx")
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    client_support = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")
    business_support = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    shared_support = _read("apps/web/src/screens/support/SurfaceSupportPrimitives.tsx")

    assert "cursor?: string" in orders_api
    assert 'params.set("cursor", cursor)' in orders_api
    assert "myOrdersNextCursor" in orders_model
    assert "loadMoreMyOrders" in orders_model
    assert "appendUniqueById" in orders_model
    assert "orderListRequestIdRef.current !== requestId" in orders_model
    assert "ordersLoadedPageCountRef" in orders_model
    assert "loadMoreMyOrders" in client_model
    assert "loadMoreMyOrders" in order_screen
    assert "Cargar mas" in order_screen

    assert "supportTicketsNextCursor" in support_model
    assert "loadMoreSupportTickets" in support_model
    assert "appendUniqueById" in support_model
    assert "supportTicketsQuery(normalizedFilter, cursor)" in support_model
    assert "setSupportTicketsLoadingMore(false)" in support_model
    for screen in (client_support, business_support):
        assert "supportTicketsNextCursor" in screen
        assert "loadMoreSupportTickets" in screen
        assert "SurfaceSupportInbox" in screen
    assert "Cargar mas" in shared_support
