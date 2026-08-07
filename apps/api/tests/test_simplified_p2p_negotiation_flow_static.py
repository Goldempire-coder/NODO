from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _read_client_chat_surface() -> str:
    paths = (
        "apps/web/src/screens/client/ClientOrderChatScreen.tsx",
        "apps/web/src/screens/client/chat/ClientChatMessageList.tsx",
        "apps/web/src/screens/client/chat/ClientPaymentDetailsBubble.tsx",
        "apps/web/src/screens/client/chat/ClientReceiverDetailsBubble.tsx",
        "apps/web/src/screens/client/chat/ClientOrderRatingBubble.tsx",
        "apps/web/src/hooks/workspace/useClientOrderChatSync.ts",
    )
    return "\n".join(_read(path) for path in paths)


def _read_client_chat_model() -> str:
    return "\n".join(
        _read(path)
        for path in (
            "apps/web/src/hooks/workspace/useClientChatDisputesModel.ts",
            "apps/web/src/hooks/workspace/useClientChatComposerModel.ts",
        )
    )


def _read_business_chat_surface() -> str:
    paths = (
        "apps/web/src/screens/business-app/BusinessChatScreen.tsx",
        "apps/web/src/screens/business-app/chat/BusinessChatMessageList.tsx",
        "apps/web/src/screens/business-app/chat/BusinessReceiverDetailsBubble.tsx",
        "apps/web/src/screens/business-app/chat/BusinessChatActionDock.tsx",
        "apps/web/src/screens/business-app/chat/BusinessChatComposer.tsx",
    )
    return "\n".join(_read(path) for path in paths)


def _read_business_chat_model() -> str:
    paths = (
        "apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts",
        "apps/web/src/hooks/business-mini-app/chat/businessChatShared.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatSession.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatComposer.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatAttachments.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessPaymentShareActions.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatOrderActions.ts",
    )
    return "\n".join(_read(path) for path in paths)


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


def test_client_payment_flow_uses_explicit_types_and_react_dependencies() -> None:
    payment_types = _read("apps/web/src/types/payments.ts")
    payment_api = _read("apps/web/src/api/paymentReports.ts")
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    main_button = _read("apps/web/src/hooks/workspace/useClientTelegramMainButton.ts")
    workspace_model = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")

    assert "PaymentReportPayload" in payment_types
    assert "PaymentEvidenceUploadResult" in payment_types
    assert "PaymentReportResult" in payment_types
    assert "payload: PaymentReportPayload" in payment_api
    assert "<any>" not in payment_model
    assert "dependencies: unknown[]" not in main_button
    assert "...dependencies" not in main_button
    assert "dependencies:" not in workspace_model


def test_chat_uses_one_compact_payment_details_flow_for_zelle_and_usdt() -> None:
    client_chat = _read_client_chat_surface()
    business_chat = _read_business_chat_surface()
    business_chat_model = _read_business_chat_model()
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")

    assert "chatCapabilities.can_report_payment" in client_chat
    assert 'paymentReportMethod === "usdt_trc20" ? "USDT enviado" : "Zelle enviado"' in client_chat
    assert "No envies el pago" in client_chat
    assert "const canSharePaymentDetails = chatCapabilities.can_share_payment_details" in business_chat
    assert 'currentOrder?.payment_method_snapshot === "usdt_trc20"' in business_chat
    assert '"Compartir wallet"' in business_chat
    assert "/share-payment-details" in _read("apps/web/src/api/chat.ts")
    assert "Confirma con el negocio la red exacta antes de enviar." in client_chat
    assert "Compartir datos de pago" in business_chat
    assert "shareConfiguredPaymentDetails" in business_chat_model
    assert "Copiar" in client_chat
    assert "instructions.payment_instructions.account_value" in client_chat
    assert "isAutomaticZelleDetails" in client_chat
    assert "business-order-chat-action-dock__hash" not in client_chat
    assert "Identificador de transaccion" not in client_chat
    assert 'className="business-order-chat-payment-action"' in business_chat
    assert "readOnly" in payment_screen
    assert "sanitizeDecimalInput" not in payment_screen
    assert 'className="business-card"' not in business_chat
    assert 'className="business-card"' not in client_chat


def test_usdt_copy_is_simple_but_the_order_network_remains_explicit() -> None:
    marketplace = _read("apps/web/src/screens/client/ClientMarketplaceScreens.tsx")
    client_chat = _read_client_chat_surface()
    payment_helpers = _read(
        "apps/web/src/hooks/business-mini-app/businessPaymentMethodHelpers.ts"
    )
    globals_css = _read("apps/web/src/app/globals.css")

    assert "USDT TRC20" not in marketplace
    assert "formatPaymentMethod(methodType)" in client_chat
    assert "paymentMethodCurrencyPresentation(methodType)" in client_chat
    assert "Confirma con el negocio la red exacta antes de enviar." in client_chat
    assert "instructions.payment_instructions.network" in client_chat
    assert "Por ahora NODO solo admite wallets USDT en TRC20." not in payment_helpers
    assert "Revisa la wallet USDT. Confirma la red exacta con el cliente por chat." in payment_helpers
    assert "margin-inline-start: 2px;" in globals_css


def test_slice_50b2_payment_mobile_is_structured_inside_compact_chat_ui() -> None:
    client_chat = _read_client_chat_surface()
    chat_notifications = _read("apps/api/app/modules/notifications/chat_notifications.py")
    chat_service = _read("apps/api/app/modules/chat/service.py")

    assert "Pago movil:\\nBanco:\\nTelefono:\\nCedula:\\nTitular:" not in client_chat
    assert "receiverDetailsForm" in client_chat
    assert "shareReceiverDetails" in client_chat
    assert "Compartir Pago Movil" in client_chat
    assert "Banco de Venezuela" in client_chat
    assert 'type="tel"' in client_chat
    assert "can_mark_delivered" in chat_service
    assert 'order.status == "payment_confirmed"' in chat_service
    assert "message.body" not in chat_notifications
    assert 'metadata_json={"order_id": order.id, "attachment_count": len(attached)}' in chat_service


def test_slice_50a_client_chat_refreshes_silently_only_while_visible() -> None:
    client_chat_sync = _read("apps/web/src/hooks/workspace/useClientOrderChatSync.ts")
    chat_model = _read_client_chat_model()

    assert "CLIENT_ORDER_CHAT_REFRESH_MS" in client_chat_sync
    assert 'view !== "order-chat"' in client_chat_sync
    assert 'document.visibilityState !== "visible"' in client_chat_sync
    assert "refreshChat({ silent: true })" in client_chat_sync
    assert "window.clearInterval(interval)" in client_chat_sync
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
    client_chat = _read_client_chat_surface()
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


def test_terminal_client_order_chat_restores_primary_navigation() -> None:
    client_shell = _read("apps/web/src/screens/client/ClientWorkspaceShell.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    assert 'view === "order-chat"' in client_shell
    assert (
        "const selectedOrderBelongsToChat = Boolean(chatOrderId) "
        "&& selectedOrder?.id === chatOrderId;"
    ) in client_shell
    assert (
        'view === "order-chat" && selectedOrderBelongsToChat && ('
        in client_shell
    )
    assert 'selectedOrder?.status === "completed"' in client_shell
    assert 'selectedOrder?.status === "cancelled"' in client_shell
    assert "isTerminalOrderChat" in client_shell
    assert "shouldShowPrimaryNav" in client_shell
    assert "business-shell--terminal-chat-nav" in client_shell
    assert ".business-shell--terminal-chat-nav .business-order-chat-messages" in global_css


def test_slice_50c_payment_report_and_business_confirmations_stay_inside_chat() -> None:
    client_chat = _read_client_chat_surface()
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")
    business_chat = _read_business_chat_surface()
    business_chat_model = _read_business_chat_model()
    business_orders = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    chat_model = _read_client_chat_model()
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
    assert "session.reloadChatSession(targetOrderId, targetSessionEpoch)" in chat_action_source
    assert "syncBusinessOrderFromChat(mutation.order)" in chat_action_source
    assert "refreshChat({ silent: true })" not in chat_action_source
    assert "Confirmar pago recibido" in business_chat
    assert "Pago Movil enviado" in business_chat
    assert "Confirmar pago" not in business_orders
    assert "Marcar enviado" not in business_orders
    assert "shouldHandleInChat" in business_orders
    assert "Pago Movil pendiente. Espera a que el cliente comparta sus datos." in business_chat
    assert "businessChatAction" in business_chat
    assert "sortChatMessages" in chat_model


def test_payment_report_state_is_scoped_to_the_active_chat_order() -> None:
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    chat_model = _read_client_chat_model()

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


def test_receiver_details_state_and_async_result_are_scoped_to_the_chat_order() -> None:
    chat_model = _read_client_chat_model()

    assert "receiverDetailsDraftsByOrder" in chat_model
    assert "receiverDetailsRequestsRef" in chat_model
    assert "const targetOrderId = chatOrderId;" in chat_model
    assert "const targetReceiverDetails = receiverDetailsForm;" in chat_model

    share_source = chat_model.split("async function shareReceiverDetails()", 1)[1].split(
        "async function confirmOrderReceived()", 1
    )[0]
    assert "shareOrderReceiverDetails" in share_source
    assert "targetOrderId" in share_source
    assert "chatOrderIdRef.current !== targetOrderId" in share_source
    stale_guard = share_source.index("chatOrderIdRef.current !== targetOrderId")
    assert stale_guard < share_source.index("setReceiverDetailsMasked(")
    assert stale_guard < share_source.index('setNotice("Pago Movil compartido.")')


def test_client_chat_open_discards_a_late_response_from_another_order() -> None:
    chat_model = _read_client_chat_model()
    open_source = chat_model.split("async function openOrderChat", 1)[1].split(
        "const refreshChat", 1
    )[0]

    assert "openChatRequestIdRef" in chat_model
    assert "const targetOrderId = orderId;" in open_source
    assert "const requestId = openChatRequestIdRef.current + 1;" in open_source
    assert "chatOrderIdRef.current !== targetOrderId" in open_source
    assert "openChatRequestIdRef.current !== requestId" in open_source
    stale_guard = open_source.index("openChatRequestIdRef.current !== requestId")
    assert stale_guard < open_source.index("setSelectedOrder(hydrated.order)")
    assert stale_guard < open_source.index("setChatMessages(sortChatMessages")


def test_client_chat_composer_and_uploads_are_scoped_by_order() -> None:
    chat_model = _read_client_chat_model()
    workspace_state = _read("apps/web/src/hooks/workspace/useClientWorkspaceState.ts")
    upload_source = chat_model.split("async function uploadChatAttachment", 1)[1].split(
        "async function sendChatMessage", 1
    )[0]
    send_source = chat_model.split("async function sendChatMessage", 1)[1].split(
        "async function openChatAttachment", 1
    )[0]

    assert "composerDraftsByOrder" in chat_model
    assert "updateComposerDraftForOrder" in chat_model
    assert "const targetOrderId = chatOrderIdRef.current;" in upload_source
    assert "updateComposerDraftForOrder(targetOrderId" in upload_source
    assert "const targetOrderId = chatOrderIdRef.current;" in send_source
    assert "const targetDraft = composerDraftsRef.current[targetOrderId]" in send_source
    assert "clearSentComposerDraft(targetOrderId, targetDraft)" in send_source
    assert "chatAttachmentLink?.orderId === chatOrderId" in chat_model
    assert "setChatBody" not in workspace_state
    assert "setChatAttachments" not in workspace_state


def test_client_chat_refresh_discards_late_errors_from_another_order() -> None:
    chat_model = _read_client_chat_model()
    refresh_source = chat_model.split("const refreshChat", 1)[1].split(
        "const composer", 1
    )[0]
    catch_source = refresh_source.split("} catch (error) {", 1)[1]

    stale_guard = catch_source.index("chatOrderIdRef.current !== targetOrderId")
    assert stale_guard < catch_source.index('setNotice(error instanceof Error')


def test_client_chat_completion_discards_a_late_response_from_another_order() -> None:
    chat_model = _read_client_chat_model()
    confirm_source = chat_model.split("async function confirmOrderReceived", 1)[1].split(
        "return {", 1
    )[0]

    assert "const targetOrderId = chatOrderIdRef.current;" in confirm_source
    assert "chatOrderIdRef.current !== targetOrderId" in confirm_source
    stale_guard = confirm_source.index("chatOrderIdRef.current !== targetOrderId")
    assert stale_guard < confirm_source.index("setSelectedOrder(completedOrder)")


def test_client_marketplace_discards_late_search_and_detail_responses() -> None:
    marketplace_model = _read("apps/web/src/hooks/workspace/useClientMarketplaceModel.ts")
    search_source = marketplace_model.split("async function searchAds()", 1)[1].split(
        "async function searchFreshForAmount", 1
    )[0]
    fresh_source = marketplace_model.split("async function searchFreshForAmount", 1)[1].split(
        "async function loadActiveMarketplace", 1
    )[0]
    list_source = marketplace_model.split("async function loadActiveMarketplace", 1)[1].split(
        "async function openAdDetail", 1
    )[0]
    detail_source = marketplace_model.split("async function openAdDetail", 1)[1].split(
        "async function prefetchActiveMarketplace", 1
    )[0]

    assert "marketplaceRequestIdRef" in marketplace_model
    for source in (search_source, fresh_source, list_source):
        assert "const requestId = marketplaceRequestIdRef.current + 1;" in source
        assert "marketplaceRequestIdRef.current = requestId;" in source
        assert "marketplaceRequestIdRef.current !== requestId" in source
        stale_guard = source.index("marketplaceRequestIdRef.current !== requestId")
        assert stale_guard < source.index("setSearchResults(data.items)")

    assert "adDetailRequestIdRef" in marketplace_model
    assert "const requestId = adDetailRequestIdRef.current + 1;" in detail_source
    assert "adDetailRequestIdRef.current = requestId;" in detail_source
    optimistic_detail_source = detail_source.split("if (optimisticAd) {", 1)[1].split(
        "if (!optimisticAd)", 1
    )[0]
    assert "setOpeningMarketplaceAdId(null)" in optimistic_detail_source
    assert "adDetailRequestIdRef.current !== requestId" in detail_source
    stale_guard = detail_source.index("adDetailRequestIdRef.current !== requestId")
    assert stale_guard < detail_source.index("setSelectedAd(data.ad)")


def test_client_orders_discards_late_list_and_detail_responses() -> None:
    orders_model = _read("apps/web/src/hooks/workspace/useRemitterOrdersModel.ts")
    list_source = orders_model.split("async function loadMyOrders", 1)[1].split(
        "async function refreshMyOrdersSilently", 1
    )[0]
    detail_source = orders_model.split("async function openOrderDetail", 1)[1].split(
        "async function extendOrder", 1
    )[0]

    assert "orderListRequestIdRef" in orders_model
    assert "const requestId = orderListRequestIdRef.current + 1;" in list_source
    assert "orderListRequestIdRef.current = requestId;" in list_source
    assert "orderListRequestIdRef.current !== requestId" in list_source
    stale_list_guard = list_source.index("orderListRequestIdRef.current !== requestId")
    assert stale_list_guard < list_source.index("setMyOrders(data.items)")

    assert "orderDetailRequestIdRef" in orders_model
    assert "const requestId = orderDetailRequestIdRef.current + 1;" in detail_source
    assert "orderDetailRequestIdRef.current = requestId;" in detail_source
    optimistic_detail_source = detail_source.split("if (optimisticOrder) {", 1)[1].split(
        "} else {", 1
    )[0]
    assert "setOpeningOrderId(null)" in optimistic_detail_source
    assert "orderDetailRequestIdRef.current !== requestId" in detail_source
    stale_detail_guard = detail_source.index("orderDetailRequestIdRef.current !== requestId")
    assert stale_detail_guard < detail_source.index("setSelectedOrder(data.order)")


def test_chat_first_contract_has_no_required_external_or_legacy_navigation() -> None:
    slice_50a_dir = "slice_50A_" + "simplified_" + "p2p_" + "negotiation_" + "flow"
    slice_50c_dir = "slice_50C_" + "native_" + "chat_surface_" + "keyboard_rescue"
    slice_50a = _read("/".join(("control_plane", "09_SLICES", slice_50a_dir, "API_CONTRACT.md")))
    slice_50c = _read("/".join(("control_plane", "09_SLICES", slice_50c_dir, "UI_CONTRACT.md")))
    orders_screen = _read("apps/web/src/screens/client/ClientOrderScreens.tsx")

    assert "then opens `report-payment` directly" not in slice_50a
    assert "does not launch a bank or wallet application" in slice_50a
    assert "reporting payment does not open a\nseparate payment screen" in slice_50c
    assert '"completed"' not in orders_screen.split("const CHAT_STATUSES", 1)[1].split("]", 1)[0]
    assert '"cancelled"' not in orders_screen.split("const CHAT_STATUSES", 1)[1].split("]", 1)[0]


def test_payment_evidence_upload_prepares_mobile_images_and_hides_raw_fetch_error() -> None:
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    payment_file = _read("apps/web/src/utils/paymentEvidenceFiles.ts")
    client_chat = _read_client_chat_surface()

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
    assert "application/pdf" not in payment_file
    assert "Usa una imagen valida JPG, PNG o WebP." in payment_file
    assert 'accept="image/jpeg,image/png,image/webp"' in client_chat


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
