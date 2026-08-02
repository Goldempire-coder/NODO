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


def test_chat_uses_one_compact_payment_details_flow_for_zelle_and_usdt() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    business_chat = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    business_chat_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")

    assert "chatCapabilities.can_report_payment" in client_chat
    assert 'paymentReportMethod === "usdt_trc20" ? "USDT enviado" : "Zelle enviado"' in client_chat
    assert "No envies el pago" in client_chat
    assert "const canSharePaymentDetails = chatCapabilities.can_share_zelle" in business_chat
    assert "Compartir datos de pago" in business_chat
    assert "shareConfiguredPaymentDetails" in business_chat_model
    assert "Copiar" in client_chat
    assert "currentPaymentInstructions.payment_instructions.account_value" in client_chat
    assert "isAutomaticZelleDetails" in client_chat
    assert "business-order-chat-action-dock__hash" not in client_chat
    assert "Identificador de transaccion" not in client_chat
    assert 'className="business-order-chat-payment-action"' in business_chat
    assert "readOnly" in payment_screen
    assert "sanitizeDecimalInput" not in payment_screen
    assert 'className="business-card"' not in business_chat
    assert 'className="business-card"' not in client_chat


def test_slice_50b2_payment_mobile_is_chat_first_not_blocking_form() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    chat_notifications = _read("apps/api/app/modules/notifications/chat_notifications.py")
    chat_service = _read("apps/api/app/modules/chat/service.py")

    assert "Pago movil:\\nBanco:\\nTelefono:\\nCedula:\\nTitular:" not in client_chat
    assert "Comparte Pago Movil" not in client_chat
    assert "receiverDetailsForm" not in client_chat
    assert "shareReceiverDetails" not in client_chat
    assert "Banco de Venezuela" not in client_chat
    assert "Escribe tu Pago Movil en el chat." in client_chat
    assert "can_mark_delivered" in chat_service
    assert 'order.status == "payment_confirmed"' in chat_service
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


def test_slice_50a_payment_action_stays_in_chat_without_intermediate_screen() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    workspace_state = _read("apps/web/src/hooks/workspace/useClientWorkspaceState.ts")
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")
    client_views = _read("apps/web/src/constants/clientViews.ts")
    client_shell = _read("apps/web/src/screens/client/ClientWorkspaceShell.tsx")

    assert "business-order-chat-action-dock" in client_chat
    assert "paymentEvidenceInputRef.current?.click()" in client_chat
    assert "submitPaymentReport()" in client_chat
    assert "openPaymentReport(chatOrderId)" in client_chat
    assert 'setView("report-payment")' not in payment_model
    assert 'setView("payment-instructions")' not in payment_model
    assert 'view === "payment-instructions"' not in payment_screen
    assert '"payment-instructions"' not in client_views
    assert '"payment-instructions"' not in client_shell
    assert "paymentInstructions.order.amount_usd" in payment_screen
    assert "readOnly" in payment_screen
    assert "selectedOrder.amount_usd" not in payment_screen
    assert 'payment_reference: ""' in workspace_state
    assert 'payment_sender_name: ""' in workspace_state
    assert 'payment_sender_account_masked: ""' in workspace_state
    open_report_source = payment_model.split("async function openPaymentReport", 1)[1].split(
        "async function uploadPaymentEvidence", 1
    )[0]
    load_instructions_source = payment_model.split(
        "async function loadPaymentInstructionsForActiveOrder", 1
    )[1].split("async function openPaymentReport", 1)[0]
    submit_report_source = payment_model.split("async function submitPaymentReport", 1)[1]
    assert "loadPaymentInstructionsForActiveOrder(orderId)" in open_report_source
    assert "loadPaymentInstructionsForActiveOrder(orderId)" in submit_report_source
    assert "paymentOrderContextRef.current" in submit_report_source
    assert 'setView("order-chat")' not in open_report_source
    assert "paymentInstructionsRequestOrderIdRef.current = orderId" in load_instructions_source
    assert "paymentOrderContextRef.current === orderId" in payment_model
    assert "USDT por red TRC20 requiere el identificador de la transaccion." not in payment_model
    assert "openingChatOrderIdRef.current === null" in payment_model
    assert "activeViewRef.current === \"order-chat\"" in payment_model
    assert "!paymentActionIsCurrent(orderId)" in load_instructions_source
    stale_guard = load_instructions_source.index("!paymentActionIsCurrent(orderId)")
    assert stale_guard < load_instructions_source.index("setPaymentInstructions(data)")
    assert 'setView(' not in open_report_source.split("catch (error)", 1)[1]
    assert "FULL_PAYMENT_FIELD" not in payment_screen


def test_slice_50c_payment_report_and_business_confirmations_stay_inside_chat() -> None:
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")
    business_chat = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    business_chat_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    business_orders = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    chat_model = _read("apps/web/src/hooks/workspace/useClientChatDisputesModel.ts")
    chat_types = _read("apps/web/src/types/chat.ts")

    assert 'setView("my-orders")' not in payment_model
    assert "loadMyOrders()" not in payment_model
    assert "refreshMyOrdersAfterPaymentReport" in payment_model
    assert 'setView("report-payment")' not in payment_model.split("async function openPaymentReport", 1)[1].split(
        "async function uploadPaymentEvidence", 1
    )[0]
    assert "refreshChatAfterPaymentReport" in payment_model
    assert "Zelle requiere comprobante." not in payment_model
    assert "payment_reference:" not in payment_model.split("isZelle", 1)[1].split(": {", 1)[0]
    assert "Referencia Zelle" not in payment_screen
    assert "Nombre del remitente" not in payment_screen
    assert "paymentEvidence" in client_chat
    assert "uploadPaymentEvidence" in client_chat
    assert "submitPaymentReport" in client_chat
    assert "Adjuntar comprobante opcional" in client_chat
    payment_action = client_chat.split("business-order-chat-payment-action", 1)[1].split("</button>", 1)[0]
    assert "!paymentEvidence" not in payment_action
    assert "business-order-chat-action-dock" in client_chat
    assert "paymentEvidenceInputRef.current?.click()" in client_chat
    assert "Cliente marco Pago enviado" not in client_chat
    assert "can_confirm_payment" in chat_types
    assert "can_mark_delivered" in chat_types
    assert "confirmBusinessPaymentInChat" in business_chat_model
    assert "markBusinessDeliveredInChat" in business_chat_model
    assert "requireUnlockedBusinessPin" in business_chat_model
    assert "routeBusinessPinError" in business_chat_model
    assert "business: access.business" in _read("apps/web/src/hooks/useBusinessMiniAppModel.ts")
    chat_action_source = business_chat_model.split("await mutateBusinessOrderRequest", 1)[1].split("} catch", 1)[0]
    assert "listOrderMessages<ChatThread<BusinessOrderSummary>>(request, targetOrderId, 50)" in chat_action_source
    assert "syncBusinessOrderFromChat(data.order)" in chat_action_source
    assert "refreshChat({ silent: true })" not in chat_action_source
    assert "Confirmar pago recibido" in business_chat
    assert "Pago Movil enviado" in business_chat
    assert "Confirmar pago" not in business_orders
    assert "Marcar enviado" not in business_orders
    assert "shouldHandleInChat" in business_orders
    assert "El cliente escribe el Pago Movil por chat" in business_chat
    assert "businessChatAction" in business_chat
    assert "sortChatMessages" in chat_model


def test_payment_report_state_is_scoped_to_the_active_chat_order() -> None:
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    chat_model = _read("apps/web/src/hooks/workspace/useClientChatDisputesModel.ts")

    assert "const orderId = paymentOrderContextRef.current;" in payment_model
    assert "paymentInstructions?.order.id === orderId ? paymentInstructions : null" in payment_model
    assert "paymentActionIsCurrent(orderId)" in payment_model
    assert "paymentInstructions?.order.id || selectedOrder?.id || chatOrderId" not in payment_model
    assert "setPaymentInstructions(null)" in chat_model
    assert "setPaymentEvidence(null)" in chat_model
    assert "setPendingPaymentReportId(null)" in chat_model
    assert "setPaymentReportForm(emptyPaymentReportForm())" in chat_model
    assert "paymentOrderContextRef.current = orderId" in chat_model
    assert "Espera a que carguen los datos de pago" in payment_model
    assert "uploadingPaymentEvidence || submittingPaymentReport || loadingPaymentInstructions" in _read(
        "apps/web/src/screens/client/ClientOrderChatScreen.tsx"
    )


def test_payment_evidence_upload_prepares_mobile_images_and_hides_raw_fetch_error() -> None:
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    payment_file = _read("apps/web/src/utils/paymentEvidenceFiles.ts")
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")

    assert "preparePaymentEvidenceFile(file)" in payment_model
    assert "paymentEvidenceUploadErrorMessage(error)" in payment_model
    assert "paymentReportSubmitErrorMessage(error)" in payment_model
    assert '"Failed to fetch"' not in payment_model
    assert "No pudimos subir el comprobante." in payment_model
    assert "No pudimos confirmar el pago. Revisa tu conexion" in payment_model
    assert "MAX_PAYMENT_EVIDENCE_UPLOAD_BYTES" in payment_file
    assert "MAX_PAYMENT_EVIDENCE_IMAGE_DIMENSION" in payment_file
    assert "canvas.toBlob" in payment_file
    assert "image/jpeg" in payment_file
    assert "application/pdf" in payment_file
    assert "Adjunta una imagen PNG/JPG/WebP o PDF." in payment_file
    assert 'accept="image/jpeg,image/png,image/webp,application/pdf"' in client_chat


def test_legacy_0041_zelle_database_contract_accepts_locked_amount_and_proof_only() -> None:
    migration = _read(
        "database/migrations/0041_simplified_zelle_payment_report_contract.up.sql"
    ).lower()
    rollback = _read(
        "database/migrations/0041_simplified_zelle_payment_report_contract.down.sql"
    ).lower()
    canonical_contract = _read(
        "control_plane/06_API_CONTRACTS/PAYMENT_REPORTS_API.md"
    )

    zelle_constraint = migration.split(
        "add constraint payment_reports_zelle_required_check", 1
    )[1].split(";", 1)[0]

    assert "drop constraint if exists payment_reports_zelle_required_check" in migration
    assert "payment_type <> 'zelle'" in zelle_constraint
    assert "proof_file_id is not null" in zelle_constraint
    assert "proof_content_sha256 is not null" in zelle_constraint
    assert "payment_reference is not null" not in zelle_constraint
    assert "payment_sender_name is not null" not in zelle_constraint
    assert "payment reports without legacy zelle sender fields require review" in rollback
    assert "payment_reference is not null" in rollback
    assert "payment_sender_name is not null" in rollback
    assert "delete from" not in migration
    assert "delete from" not in rollback
    assert "payment_reference` opcional" in canonical_contract
    assert "payment_sender_name` opcional" in canonical_contract


def test_zelle_payment_evidence_is_optional_in_runtime_and_database_contract() -> None:
    migration = _read(
        "database/migrations/0042_optional_zelle_payment_evidence.up.sql"
    ).lower()
    rollback = _read(
        "database/migrations/0042_optional_zelle_payment_evidence.down.sql"
    ).lower()
    payment_builder = _read(
        "apps/api/app/modules/orders/payment_report_builder.py"
    )
    canonical_contract = _read(
        "control_plane/06_API_CONTRACTS/PAYMENT_REPORTS_API.md"
    )

    zelle_constraint = migration.split(
        "add constraint payment_reports_zelle_required_check", 1
    )[1].split(";", 1)[0]

    assert "proof_file_id is null" in zelle_constraint
    assert "proof_content_sha256 is null" in zelle_constraint
    assert "proof_file_id is not null" in zelle_constraint
    assert "proof_content_sha256 is not null" in zelle_constraint
    assert "zelle payment reports without proof require review before rollback" in rollback
    assert "delete from" not in migration
    assert "delete from" not in rollback
    assert "if proof_file_id is None and pending_payment_report_id is None" in payment_builder
    assert "comprobante es opcional" in canonical_contract


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
