from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_admin_investigation_search_is_temporary_clearable_and_scrollable() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminInvestigationScreens.tsx")
    model = _read("apps/web/src/hooks/admin-web/useAdminInvestigationModel.ts")
    web_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    css = _read("apps/web/src/app/admin-web.css")

    assert "clearInvestigationSearch" in model
    assert "EMPTY_SEARCH" in model
    assert "setInvestigationResults(EMPTY_SEARCH)" in model
    assert "setInvestigationSearched(false)" in model
    assert "lastInvestigationQuery" in model
    assert "trim() !== lastInvestigationQuery" in model
    assert "clearInvestigationSearch: investigation.clearInvestigationSearch" in web_model

    assert "Limpiar busqueda" in screen
    assert "model.clearInvestigationSearch" in screen
    assert "admin-web-investigation-results-scroll" in screen
    assert 'aria-label="Resultados de busqueda admin"' in screen
    assert 'role="region"' in screen
    assert "tabIndex={0}" in screen

    assert ".admin-web-investigation-results-scroll" in css
    assert "overflow-y: auto" in css
    assert ".admin-web-investigation-results-scroll:focus-visible" in css


def test_admin_investigation_results_can_return_to_search_and_chat_history_is_scrollable() -> None:
    web_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    investigation_model = _read("apps/web/src/hooks/admin-web/useAdminInvestigationModel.ts")
    case_model = _read("apps/web/src/hooks/admin-web/useAdminInvestigationCaseFileModel.ts")
    case_screen = _read("apps/web/src/screens/admin-web/AdminInvestigationCaseFileScreen.tsx")
    order_screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")
    chat_panel = _read("apps/web/src/screens/admin-web/AdminOrderChatEvidencePanel.tsx")

    assert "pushAdminBackView" in web_model
    assert "goBackAdminView" in web_model
    assert "adminCanGoBack" in web_model
    assert "adminBackLabel" in web_model
    assert "pushBackView: pushAdminBackView" in web_model

    assert "pushBackView" in investigation_model
    assert 'pushBackView("investigation")' in investigation_model
    assert "pushBackView" in case_model
    assert 'pushBackView("case-file")' in case_model

    assert "Volver a buscar" in case_screen
    assert "model.goBackAdminView" in case_screen
    assert "model.goBackAdminView" in order_screen
    assert "model.adminBackLabel" in order_screen
    assert "adminCanGoBack" in order_screen

    assert 'aria-label="Historial del chat de la orden"' in chat_panel
    assert 'role="region"' in chat_panel
    assert "tabIndex={0}" in chat_panel
