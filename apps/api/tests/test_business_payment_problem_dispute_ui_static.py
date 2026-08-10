from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_business_payment_problem_uses_formal_dispute_contract() -> None:
    screen = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    dashboard = _read("apps/web/src/screens/business-app/BusinessDashboardScreen.tsx")
    helpers = _read("apps/web/src/hooks/business-mini-app/helpers.ts")
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    orders_api = _read("apps/web/src/api/businessOrders.ts")
    disputes_api = _read("apps/web/src/api/chat.ts")
    types = _read("apps/web/src/types/orders.ts")

    assert "can_open_dispute: boolean" in types
    assert '"report-payment-problem"' in model
    assert "openOrderDispute" in model
    assert 'reason: "payment_not_received_or_incomplete"' in model
    assert "evidence_file_ids: []" in model
    assert "business_order_report_payment_problem" in model
    assert "Problema reportado. NODO revisará la operación." in model
    assert "Reportar problema con pago" in screen
    assert "Reportando..." in screen
    assert "canReportPaymentProblem(businessOrderDetail.order)" in screen
    assert "`/api/v1/orders/${orderId}/disputes`" in disputes_api
    assert '"Idempotency-Key": idempotencyKey' in disputes_api
    assert '"reject-payment-report"' not in orders_api

    combined = "\n".join((screen, dashboard, helpers, model, orders_api))
    for legacy in (
        "Rechazar reporte",
        "Rechazando...",
        "Reporte rechazado",
        "Para rechazar un reporte",
        "business_order_reject_payment_report",
    ):
        assert legacy not in combined


def test_business_payment_problem_preserves_order_isolation_and_durable_success() -> None:
    model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")

    assert "targetOrderId" in model
    assert "targetRequestEpoch" in model
    assert "isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)" in model
    assert "businessOrderActionsRef.current.has(targetOrderId)" in model
    assert "businessOrderActionsRef.current.set(targetOrderId, action)" in model
    assert "reconcileBusinessOrder(reconciledOrder)" in model
    assert "setBusinessOrderDetail((current) => {" in model
    assert "current.order.id !== order.id" in model
    assert "return { ...current, order };" in model
    assert "clearIdempotencyKey(idempotencyScope);" in model
    assert "No pudimos actualizar el detalle; toca Actualizar." in model

    mutation_position = model.index("await openOrderDispute")
    clear_position = model.index("clearIdempotencyKey(idempotencyScope);")
    reconcile_position = model.index("reconcileBusinessOrder(reconciledOrder)")
    refresh_position = model.index("await getBusinessOrder<BusinessOrderDetail>", mutation_position)
    assert mutation_position < clear_position < reconcile_position < refresh_position
    assert model.count("await openOrderDispute") == 1


def test_business_payment_problem_remains_outside_chat() -> None:
    chat_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    chat_actions = _read("apps/web/src/hooks/business-mini-app/chat/useBusinessChatOrderActions.ts")
    chat_screen = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")

    for source in (chat_model, chat_actions, chat_screen):
        assert "openOrderDispute" not in source
        assert "Reportar problema con pago" not in source
