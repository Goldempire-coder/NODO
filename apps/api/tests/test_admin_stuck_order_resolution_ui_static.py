from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_admin_payment_rejected_resolution_uses_dispute_workflow() -> None:
    api = _read("apps/web/src/api/admin.ts")
    admin_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    model = _read("apps/web/src/hooks/admin-web/useAdminOrdersDisputesModel.ts")
    screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")

    assert "openAdminOrderDispute" in api
    assert "/api/v1/admin/orders/${orderId}/open-dispute" in api
    assert "resolveAdminStuckOrder" in model
    assert "openAdminOrderDispute" in model
    assert "resolveAdminDispute" in model
    assert model.index("openAdminOrderDispute") < model.index("resolveAdminDispute")
    assert 'status !== "payment_rejected"' in model
    assert "getIdempotencyKey" in model
    assert "openOrder(order.id)" in model
    assert "openDispute(opened.dispute.id)" in model
    assert "La investigacion se abrio, pero falta completar la resolucion" in model
    assert "resolveAdminStuckOrder: ordersDisputes.resolveAdminStuckOrder" in admin_model
    assert "stuckOrderResolutionPreview: ordersDisputes.stuckOrderResolutionPreview" in admin_model

    assert 'order?.status === "payment_rejected"' in screen
    assert "Resolver orden" in screen
    assert "Cancelar por pago no comprobado" in screen
    assert "Mantener en investigacion" in screen
    assert "Resolver a favor del cliente" in screen
    assert "Resolver a favor del negocio" in screen
    assert 'label="Razon obligatoria"' in screen
    assert "model.resolveAdminStuckOrder()" in screen

    forbidden_direct_calls = (
        "cancelAdminOrder",
        "completeAdminOrder",
        "confirmAdminOrderPayment",
    )
    for forbidden in forbidden_direct_calls:
        assert forbidden not in model
        assert forbidden not in screen


def test_admin_stuck_order_resolution_maps_only_owner_approved_effects() -> None:
    model = _read("apps/web/src/hooks/admin-web/useAdminOrdersDisputesModel.ts")

    for resolution_type in (
        "cancelled:",
        "keep_under_review:",
        "remitter_favored:",
        "business_favored:",
    ):
        assert resolution_type in model

    assert '"completed"' not in model
    assert "queueCriticalAction" in model
    assert "requiresReason" in model
    assert "setReason(\"\")" in model
    assert "order.public_order_code" in model
    assert "Resultado:" in model
    assert "Efecto esperado:" in model
    assert "Libera el credito publicitario bloqueado y la capacidad reservada. No consume credito." in model
    assert "Mantiene la investigacion sin mover credito, capacidad ni anuncio." in model
    assert "Cancela la orden y consume el credito publicitario segun el contrato vigente." in model
    assert "Completa la orden y consume el credito publicitario segun el contrato vigente." in model


def test_client_uses_safe_terminal_projection_for_admin_rejected_payment() -> None:
    types = _read("apps/web/src/types/orders.ts")
    presentation = _read("apps/web/src/screens/client/clientOrderPresentation.ts")
    screen = _read("apps/web/src/screens/client/ClientOrderScreens.tsx")

    assert "terminal_display_status" in types
    assert "payment_rejected_admin_review" in types
    assert "clientOrderStatusLabel" in presentation
    assert 'return "Pago rechazado"' in presentation
    assert "clientOrderStatusLabel(selectedOrder)" in screen
    assert "clientOrderStatusLabel(order)" in screen


def test_admin_stuck_order_resolution_layout_keeps_confirmation_visible() -> None:
    shell = _read("apps/web/src/screens/admin-web/AdminWebShell.tsx")
    screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert shell.index("<AdminWebScreens model={model} />") < shell.index("admin-web-confirm")
    assert "admin-web-order-resolution" in screen
    assert screen.index("admin-web-order-resolution") < screen.index("admin-order-detail-summary")
    assert screen.index("admin-web-order-resolution") < screen.index("{order ? <AdminOrderChatEvidencePanel")
    assert "admin-web-order-resolution__header" in screen
    assert "admin-web-order-resolution__body" in screen
    assert "admin-order-detail-summary" in screen

    assert ".admin-web-confirm {" in css
    assert "position: sticky;" in css
    assert "bottom: 0;" in css
    assert "flex: 0 0 auto;" in css
    assert "max-height: min(156px, 28dvh);" in css
    assert "overflow-y: auto;" in css
    assert ".admin-web-order-resolution {" in css
    assert "max-height: min(292px, 38dvh);" in css
    assert ".admin-web-order-resolution__body" in css
    assert ".admin-web-order-resolution .admin-web-field textarea" in css
    assert "min-height: 56px;" in css
    assert "max-height: 86px;" in css
    assert ".admin-web-confirm .admin-web-actions button" in css
