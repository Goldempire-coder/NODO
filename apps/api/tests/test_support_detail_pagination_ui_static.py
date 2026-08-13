from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_support_detail_ui_loads_history_explicitly_and_polling_preserves_loaded_pages() -> None:
    support_types = _read("apps/web/src/types/support.ts")
    support_api = _read("apps/web/src/api/support.ts")
    shared_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    admin_model = _read("apps/web/src/hooks/admin-web/useAdminSupportModel.ts")
    shared_thread = _read("apps/web/src/screens/support/SurfaceSupportPrimitives.tsx")
    admin_screen = _read("apps/web/src/screens/admin-web/AdminSupportScreens.tsx")

    assert "messages_next_cursor" in support_types
    assert "events_next_cursor" in support_types
    assert 'params.set("messages_cursor"' in support_api
    assert "loadMoreSupportMessages" in shared_model
    assert "loadMoreSupportMessages" in admin_model
    assert "mergeSupportTicketPage" in shared_model
    assert "mergeSupportTicketPage" in admin_model
    assert "preserveHistoryCursor: true" in shared_model
    assert "preserveHistoryCursor: true" in admin_model
    assert "Cargar mensajes anteriores" in shared_thread
    assert "Cargar mensajes anteriores" in admin_screen


def test_support_polling_keeps_visible_only_and_no_overlap_guards() -> None:
    client_screen = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")
    business_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    shared_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    admin_polling = _read("apps/web/src/hooks/admin-web/useVisibleAdminPolling.ts")

    assert "useVisibleSurfacePolling" in client_screen
    assert "useVisibleSurfacePolling" in business_screen
    assert "supportRefreshInFlightRef.current" in shared_model
    assert 'document.visibilityState !== "visible"' in admin_polling
    assert "inFlightRef.current" in admin_polling


def test_admin_assignment_preserves_loaded_support_history() -> None:
    admin_model = _read("apps/web/src/hooks/admin-web/useAdminSupportModel.ts")
    assignment = admin_model.split("const assignSupportTicket = useCallback", 1)[1].split(
        "const refreshSupportTicket", 1
    )[0]

    assert "mergeSupportTicketPage(current, ticket, { preserveHistoryCursor: true })" in assignment
    assert "current?.id === ticketId ? ticket : current" not in assignment
