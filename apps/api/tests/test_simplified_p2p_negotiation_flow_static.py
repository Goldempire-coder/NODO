from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_slice_50a_client_confirms_minimal_quote_before_post_and_opens_chat() -> None:
    marketplace = _read("apps/web/src/screens/client/ClientMarketplaceScreens.tsx")
    orders_screen = _read("apps/web/src/screens/client/ClientOrderScreens.tsx")
    orders_model = _read("apps/web/src/hooks/workspace/useRemitterOrdersModel.ts")
    orders_api = _read("apps/web/src/api/orders.ts")

    assert 'setView("create-order")' in marketplace
    assert "Confirmar negociacion" in orders_screen
    assert "Monto que entregas" in orders_screen
    assert "Monto que recibe" in orders_screen
    assert "Banco receptor" not in orders_screen
    assert "Telefono receptor" not in orders_screen
    assert "Documento receptor" not in orders_screen
    assert "Titular receptor" not in orders_screen
    assert "receiver_data:" not in orders_model
    assert "receiver_data?:" in orders_api
    assert "expected_rate_bs_per_usd: selectedAd.rate_bs_per_usd" in orders_model
    assert "expected_rate_bs_per_usd?: string" in orders_api
    assert "await openOrderChat(data.order.id)" in orders_model
    assert 'setView("order-summary")' not in orders_model.split("async function createOrder()", 1)[1].split(
        "async function loadMyOrders", 1
    )[0]


def test_slice_50a_chat_gates_payment_and_exposes_only_compact_zelle_action() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    business_chat = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    business_chat_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")

    assert "chatCapabilities.can_report_payment" in client_chat
    assert "Pago enviado" in client_chat
    assert "No envíes Zelle" in client_chat
    assert "chatCapabilities.can_share_zelle" in business_chat
    assert "Enviar Zelle" in business_chat
    assert "shareConfiguredZelle" in business_chat_model
    assert 'className="business-order-chat-payment-action"' in business_chat
    assert "readOnly" in payment_screen
    assert "sanitizeDecimalInput" not in payment_screen
    assert 'className="business-card"' not in business_chat
    assert 'className="business-card"' not in client_chat


def test_slice_50b1_payment_mobile_uses_structured_resource_not_chat_body() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    chat_notifications = _read("apps/api/app/modules/notifications/chat_notifications.py")
    chat_service = _read("apps/api/app/modules/chat/service.py")

    assert "Pago movil:\\nBanco:\\nTelefono:\\nCedula:\\nTitular:" not in client_chat
    assert "shareReceiverDetails" in client_chat
    assert "receiverDetailsForm" in client_chat
    assert "message.body" not in chat_notifications
    assert 'metadata_json={"order_id": order.id, "attachment_count": len(attached)}' in chat_service


def test_slice_50a_client_chat_refreshes_silently_only_while_visible() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    chat_model = _read("apps/web/src/hooks/workspace/useClientChatDisputesModel.ts")

    assert "CLIENT_ORDER_CHAT_REFRESH_MS" in client_chat
    assert 'model.view !== "order-chat"' in client_chat
    assert 'document.visibilityState !== "visible"' in client_chat
    assert "refreshChat({ silent: true })" in client_chat
    assert "window.clearInterval(interval)" in client_chat
    assert "refreshingChatRef.current" in chat_model
    assert "refreshingChatRef.current = true" in chat_model
    assert "refreshingChatRef.current = false" in chat_model
    refresh_source = chat_model.split("const refreshChat", 1)[1].split(
        "async function uploadChatAttachment", 1
    )[0]
    refresh_catch = refresh_source.split("catch (error)", 1)[1].split(
        "} finally", 1
    )[0]
    assert "setChatMessages(" not in refresh_catch
    assert "setChatCapabilities(" not in refresh_catch


def test_slice_50a_payment_action_opens_compact_report_without_intermediate_screen() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")
    client_views = _read("apps/web/src/constants/clientViews.ts")
    client_shell = _read("apps/web/src/screens/client/ClientWorkspaceShell.tsx")

    assert "openPaymentReport" in client_chat
    assert 'setView("report-payment")' in payment_model
    assert 'setView("payment-instructions")' not in payment_model
    assert 'view === "payment-instructions"' not in payment_screen
    assert '"payment-instructions"' not in client_views
    assert '"payment-instructions"' not in client_shell
    assert "paymentInstructions.order.amount_usd" in payment_screen
    assert "readOnly" in payment_screen
    assert "selectedOrder.amount_usd" not in payment_screen
    assert 'payment_reference: ""' in payment_model
    assert 'payment_sender_name: ""' in payment_model
    assert 'payment_sender_account_masked: ""' in payment_model
    open_report_source = payment_model.split("async function openPaymentReport", 1)[1].split(
        "async function uploadPaymentEvidence", 1
    )[0]
    assert open_report_source.index("await getPaymentInstructions") < open_report_source.index(
        'setView("report-payment")'
    )
    assert "paymentReportTargetOrderIdRef.current = orderId" in open_report_source
    assert "activeChatOrderIdRef.current === orderId" in payment_model
    assert "openingChatOrderIdRef.current === null" in payment_model
    assert "activeViewRef.current === \"order-chat\"" in payment_model
    assert "if (!paymentReportTargetIsCurrent(orderId))" in open_report_source
    stale_guard = open_report_source.index("if (!paymentReportTargetIsCurrent(orderId))")
    assert stale_guard < open_report_source.index("setPaymentInstructions(data)")
    assert stale_guard < open_report_source.index('setView("report-payment")')
    assert 'setView(' not in open_report_source.split("catch (error)", 1)[1]
    assert "FULL_PAYMENT_FIELD" not in payment_screen


def test_slice_50b1_business_order_detail_ignores_legacy_receiver_data() -> None:
    business_orders = _read(
        "apps/web/src/screens/business-app/BusinessOrdersScreens.tsx"
    )

    assert "Pago Movil pendiente en chat" in business_orders
    assert "capabilities.receiver_details_shared" in business_orders
    assert "hasLegacyReceiverData" not in business_orders
    assert '|| "Banco"' not in business_orders
    assert '|| "enmascarado"' not in business_orders
    assert '|| "Titular"' not in business_orders
