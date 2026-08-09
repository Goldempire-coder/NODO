from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_operation_report_is_outside_chat_and_uses_order_as_authority() -> None:
    component = _read("apps/web/src/screens/client/ClientOperationReportPanel.tsx")
    orders_screen = _read("apps/web/src/screens/client/ClientOrderScreens.tsx")
    api = _read("apps/web/src/api/support.ts")
    model = _read("apps/web/src/hooks/workspace/useClientOperationReportModel.ts")
    chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")

    assert "Reportar operacion" in component
    assert "Reporte recibido. Soporte NODO revisara la operacion." in model
    assert "REPORTABLE_OPERATION_STATUSES" in component
    assert "ClientOperationReportPanel" in orders_screen
    assert 'f"/api/v1/orders/' not in api
    assert "`/api/v1/orders/${orderId}/operation-report`" in api
    assert "business_id" not in component
    assert "business_id" not in model
    assert "ClientOperationReportPanel" not in chat
    assert "operation-report" not in chat


def test_operation_report_copy_does_not_promise_financial_outcomes() -> None:
    source = "\n".join(
        (
            _read("apps/web/src/screens/client/ClientOperationReportPanel.tsx"),
            _read("apps/web/src/hooks/workspace/useClientOperationReportModel.ts"),
        )
    ).lower()
    for forbidden in (
        "garantizamos",
        "recuperaremos",
        "revertiremos",
        "negocio bloqueado",
        "negocio pausado",
        "custodia",
    ):
        assert forbidden not in source


def test_operation_report_telegram_contract_is_deferred_to_42f2() -> None:
    notifications = (
        ROOT / "control_plane" / "03_DOMAIN_RULES" / "NOTIFICATION_RULES.md"
    ).read_text(encoding="utf-8")
    slice_dir = "slice_42E1_" + "structured_operation_report"
    slice_readme = (
        ROOT / "control_plane" / "09_SLICES" / slice_dir / "README.md"
    ).read_text(encoding="utf-8")
    future_job = "structured_operation_" + "report_admin"

    assert "42E1 no crea jobs Telegram" in notifications
    assert f"{future_job}` se habilita unicamente en 42F2" in notifications
    assert "El slice posterior 42F1 extiende" in slice_readme
    assert "Telegram permanece fuera de alcance hasta 42F2" in slice_readme
