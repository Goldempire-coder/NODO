from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


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
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatSession.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatComposer.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatAttachments.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessPaymentShareActions.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatOrderActions.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatPolling.ts",
    )
    return "\n".join(_read(path) for path in paths)


def test_business_order_chat_uses_native_chat_surface_not_table_rows() -> None:
    chat_screen = _read_business_chat_surface()
    client_chat = _read_client_chat_surface()
    business_shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    client_shell = _read("apps/web/src/screens/client/ClientWorkspaceShell.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    for source in [chat_screen, client_chat]:
        assert "business-order-chat" in source
        assert "business-order-chat-messages" in source
        assert "business-order-chat-message business-order-chat-message--mine" in source
        assert "business-order-chat-composer" in source
        assert "business-order-chat-composer__input" in source
        assert "business-order-chat-system-bubble" in source
        assert "business-order-chat__summary" not in source
        assert 'className="business-order-chat-payment-bar"' not in source
        assert "RefreshIcon" not in source
        assert "rows={1}" in source
        assert "SendIcon" in source
    for shell in [business_shell, client_shell]:
        assert "isNativeChatSurface" in shell
        assert "business-shell--native-chat" in shell
        assert "native-chat-back" in shell
    assert ".business-order-chat {" in global_css
    assert ".business-order-chat-messages {" in global_css
    assert ".business-order-chat-composer {" in global_css
    assert ".business-shell--native-chat {" in global_css
    native_shell_css = global_css.split(".business-shell--native-chat {", 1)[1].split("}", 1)[0]
    assert "display: block;" in native_shell_css
    assert ".native-chat-back {" in global_css
    assert "overflow-y: auto;" in global_css
    assert "grid-template-rows: minmax(0, 1fr) auto;" in global_css


def test_business_order_chat_has_compact_attachment_and_keyboard_safe_typing_mode() -> None:
    chat_screen = _read_business_chat_surface()
    client_chat = _read_client_chat_surface()
    global_css = _read("apps/web/src/app/globals.css")

    assert "PaperclipIcon" in chat_screen
    assert "fileInputRef.current?.click()" in chat_screen
    assert 'accept="image/jpeg,image/png,image/webp"' in chat_screen
    assert 'accept="image/*,application/pdf"' not in chat_screen
    assert 'aria-label="Adjuntar comprobante o soporte"' in chat_screen
    for source in [chat_screen, client_chat]:
        assert '"business-order-chat"' in source
        assert "business-order-chat--typing" not in source
        assert "focusComposer" not in source
        assert "blurComposer" not in source
        assert "window.setTimeout(scrollMessagesToEnd, 260);" not in source
    assert "business-shell--keyboard-active" in _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    assert "useMobileKeyboardViewport" in _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    assert "window.visualViewport" in _read("apps/web/src/hooks/useMobileKeyboardViewport.ts")
    assert "--nodo-viewport-height" in global_css
    assert ".app-shell:has(.business-order-chat--typing) .primary-nav" not in global_css
    assert ".business-shell--keyboard-active .primary-nav" in global_css
    assert ".primary-nav--hidden" in global_css
    assert ".business-order-chat--typing" not in global_css
    assert "grid-template-columns: 40px minmax(0, 1fr) 44px;" in global_css
    assert "font-size: 16px;" in global_css.split(".business-order-chat-composer__input", 1)[1].split("}", 1)[0]
    assert "-webkit-overflow-scrolling: touch;" in global_css
    assert "touch-action: pan-y;" in global_css
    assert "business-order-chat-system-bubble" in chat_screen
    assert "business-order-chat-attachment__button" in chat_screen
    assert "openChatAttachment" in chat_screen
    assert "Adjunto privado" not in chat_screen


def test_client_and_business_support_keep_stable_layout_when_keyboard_opens() -> None:
    business_support = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    client_support = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")
    keyboard_hook = _read("apps/web/src/hooks/useMobileKeyboardViewport.ts")
    global_css = _read("apps/web/src/app/globals.css")

    for source in [business_support, client_support]:
        assert "composerFocused" not in source
        assert "focusComposer" not in source
        assert "blurComposer" not in source
        assert "business-support--typing" not in source
        assert "window.setTimeout(scrollMessagesToEnd" not in source

    form_control_css = global_css.split("input,", 1)[1].split("}", 1)[0]
    assert "font-size: 16px;" in form_control_css
    support_composer_css = global_css.split(".surface-support-composer__input", 1)[1].split("}", 1)[0]
    assert "font-size: 16px;" in support_composer_css
    assert ".business-support--typing" not in global_css
    assert "visualViewport?.addEventListener(\"scroll\"" not in keyboard_hook
    assert "window.setTimeout" not in keyboard_hook
    assert "window.requestAnimationFrame" in keyboard_hook
    assert "isEditableElement(document.activeElement) &&" in keyboard_hook


def test_business_order_chat_refreshes_silently_and_prevents_duplicate_mutations() -> None:
    chat_model = _read_business_chat_model()
    chat_screen = _read_business_chat_surface()
    chat_types = _read("apps/web/src/types/chat.ts")
    app_model = _read("apps/web/src/hooks/useBusinessMiniAppModel.ts")

    assert "BUSINESS_ORDER_CHAT_REFRESH_MS = 5000" in chat_model
    assert "void refreshChat({ silent: true });" in chat_model
    assert 'isChatView: model.view === "business-chat"' in chat_screen
    assert "if (!chatOrderId || !isChatView)" in chat_model
    assert 'document.visibilityState !== "visible"' in chat_model
    assert "const refreshChat = useCallback(async (options?: { silent?: boolean })" in chat_model
    assert "if (!options?.silent)" in chat_model
    assert "listOrderMessages<ChatThread<BusinessOrderSummary>>(request, orderId, 50)" in chat_model
    assert "reloadChatSession(targetOrderId, targetSessionEpoch)" in chat_model
    assert "refreshingChatRef.current" in chat_model
    assert "isCurrentChatSession(targetOrderId, targetSessionEpoch)" in chat_model
    assert "sendingChatMessageRef.current" in chat_model
    assert "uploadingChatAttachmentRef.current" in chat_model
    assert "openingOrderDisputeRef.current" not in chat_model
    assert "syncBusinessOrderFromChat(data.order)" in chat_model
    assert "ChatThread<BusinessOrderSummary>" in chat_model
    assert "order: TOrder" in chat_types
    assert "syncBusinessOrderFromChat: orders.syncBusinessOrderFromChat" in app_model
    assert "chatDraftsByOrderRef.current[targetOrderId]" in chat_model
    assert "(!body && attachmentIds.length === 0)" in chat_model
    assert "clearSubmittedChatDraft(targetOrderId, body)" in chat_model
    assert "clearSubmittedChatAttachments(targetOrderId, attachmentIds)" in chat_model
    session_model = _read(
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatSession.ts"
    )
    refresh_source = session_model.split("const refreshChatSession", 1)[1].split(
        "const refreshChat =", 1
    )[0]
    refresh_catch = refresh_source.split("catch (error)", 1)[1].split(
        "} finally", 1
    )[0]
    assert "setChatMessages(" not in refresh_catch
    assert "setChatCapabilities(" not in refresh_catch


def test_repeated_silent_chat_refresh_failure_becomes_visible_inline() -> None:
    session_model = _read(
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatSession.ts"
    )
    chat_screen = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    message_list = _read(
        "apps/web/src/screens/business-app/chat/BusinessChatMessageList.tsx"
    )

    assert "SILENT_CHAT_REFRESH_FAILURE_THRESHOLD" in session_model
    assert "silentRefreshFailureCountRef" in session_model
    assert "chatRefreshError" in session_model
    assert "isCurrentChatSession(targetOrderId, targetSessionEpoch)" in session_model
    assert "setChatRefreshError" in session_model
    assert "chatRefreshError={chatRefreshError}" in chat_screen
    assert "chatRefreshError" in message_list
    assert "Actualizar" in message_list


def test_order_chat_suppresses_global_attention_and_success_toasts_while_open() -> None:
    business_shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    client_shell = _read("apps/web/src/screens/client/ClientWorkspaceShell.tsx")
    business_model = _read_business_chat_model()
    client_model = _read_client_chat_model()
    client_chat = _read_client_chat_surface()

    assert 'view === "business-chat"' in business_shell
    assert "attentionBannerItem" in business_shell
    assert "item={attentionBannerItem}" in business_shell
    assert 'view === "order-chat"' in client_shell
    assert "attentionBannerItem" in client_shell
    assert "item={attentionBannerItem}" in client_shell
    assert 'setNotice("Mensaje enviado.")' not in business_model
    assert 'setNotice("Mensaje registrado.")' not in client_model
    assert "business-order-chat-system-bubble" in client_chat
    assert "business-order-chat-attachment__button" in client_chat
    assert "openChatAttachment" in client_chat
    assert "Adjunto privado" not in client_chat


def test_order_chat_keeps_visible_attachment_fallback_for_telegram_webview() -> None:
    business_model = _read_business_chat_model()
    business_chat = _read_business_chat_surface()
    client_model = _read_client_chat_model()
    client_chat = _read_client_chat_surface()
    telegram_theme = _read("apps/web/src/theme/telegramTheme.ts")
    global_css = _read("apps/web/src/app/globals.css")

    for source in [business_model, client_model]:
        assert "chatAttachmentLink" in source
        assert "setChatAttachmentLink" in source
        assert "getTelegramWebApp()?.openLink" in source
        assert "window.open" in source

    for source in [business_chat, client_chat]:
        assert "business-order-chat-attachment-preview" in source
        assert "<img" in source
        assert "Abrir imagen" in source
        assert "Cerrar" in source

    assert "openLink?: (url: string" in telegram_theme
    assert ".business-order-chat-attachment-preview {" in global_css
    assert ".business-order-chat-attachment-preview img {" in global_css


def test_business_order_list_marks_new_and_actionable_orders_green() -> None:
    business_orders = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    assert "requiresBusinessAttention(order)" in business_orders
    assert 'order.status === "waiting_payment"' in business_orders
    assert 'order.status === "waiting_payment" ? "Nueva"' in business_orders
    assert 'order-row--attention' in business_orders
    assert "Abrir chat" in business_orders
    assert ".order-row--attention {" in global_css
    assert ".order-row__badge {" in global_css


def test_order_chat_terminal_state_keeps_history_without_composer_or_dispute_copy() -> None:
    business_chat = _read_business_chat_surface()
    client_chat = _read_client_chat_surface()
    business_model = _read_business_chat_model()

    assert "const [chatOrder, setChatOrder]" in business_model
    assert "setChatOrder(data.order)" in business_model
    assert "chatOrder?.id === chatOrderId" in business_chat
    for source in [business_chat, client_chat]:
        assert 'status === "cancelled"' in source
        assert 'status === "completed"' in source
        assert "Esta negociación está cerrada." in source
        assert "registro de la conversación" in source
        assert "respaldo" not in source.lower()
        assert "!chatIsTerminal ? (" in source
        assert "business-order-chat-composer" in source


def test_order_chat_uses_compact_role_correct_actions_and_composer_attachment() -> None:
    business_chat = _read_business_chat_surface()
    client_chat = _read_client_chat_surface()

    assert "business-order-chat-action-dock" in business_chat
    assert "Compartir datos de pago" in business_chat
    assert "Confirmar pago recibido" in business_chat
    assert '"Enviar Zelle"' not in business_chat
    assert "Pago Movil enviado" in business_chat
    assert "business-order-chat-action-dock" in client_chat
    assert "paymentEvidenceInputRef.current?.click()" in client_chat
    assert '>Foto<' not in client_chat
    assert 'paymentReportMethod === "usdt_trc20" ? "USDT enviado" : "Zelle enviado"' in client_chat
    assert "business-order-chat-action-dock__hash" not in client_chat
    assert "Identificador de transaccion" not in client_chat
    assert "Copiar" in client_chat
    assert "Pago reportado. Esperando confirmacion del negocio." in client_chat


def test_order_chat_has_no_support_or_dispute_entry_points() -> None:
    business_chat = _read_business_chat_surface()
    client_chat = _read_client_chat_surface()
    business_model = _read_business_chat_model()
    client_model = _read_client_chat_model()

    for source in [business_chat, client_chat, business_model, client_model]:
        assert "openOrderDispute" not in source
        assert "openingOrderDispute" not in source
        assert "disputeReason" not in source
    for source in [
        business_chat,
        client_chat,
        _read("apps/web/src/hooks/useBusinessMiniAppModel.ts"),
        _read("apps/web/src/hooks/useClientWorkspaceModel.ts"),
    ]:
        assert "Ir a Soporte" not in source
        assert "openBusinessOrderSupport" not in source
        assert "openClientOrderSupport" not in source
    global_css = _read("apps/web/src/app/globals.css")
    assert "business-order-chat-support-action" not in global_css


def test_order_chat_actions_refresh_in_place_without_abbreviated_identifiers() -> None:
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    orders_model = _read("apps/web/src/hooks/workspace/useRemitterOrdersModel.ts")
    client_model = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")
    business_model = _read_business_chat_model()
    business_chat = _read_business_chat_surface()
    client_chat = _read_client_chat_surface()
    business_support = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    client_support = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")
    client_payment = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")
    business_credits = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    business_credit_presentation = _read("apps/web/src/screens/business-app/businessCreditPresentation.ts")
    business_settings = _read("apps/web/src/screens/business-app/BusinessSettingsScreen.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    submit_source = payment_model.split("async function submitPaymentReport", 1)[1]
    assert "loadMyOrders()" not in submit_source
    assert "refreshMyOrdersAfterPaymentReport" in submit_source
    assert 'setView("order-chat")' not in submit_source
    assert "refreshMyOrdersAfterPaymentReport: remitterOrders.refreshMyOrdersSilently" in client_model
    silent_refresh = orders_model.split("async function refreshMyOrdersSilently", 1)[1].split(
        "async function openOrderDetail", 1
    )[0]
    assert "setView(" not in silent_refresh
    assert "const mutation = await mutateBusinessOrderRequest" in business_model
    assert "session.setCurrentChatOrder(targetOrderId, targetSessionEpoch, mutation.order)" in business_model
    assert 'chatCapabilities.can_report_payment && selectedChatOrder?.status === "waiting_payment"' in client_chat
    assert 'chatCapabilities.can_confirm_received && selectedChatOrder?.status === "delivered"' in client_chat
    assert 'chatCapabilities.can_confirm_payment && currentOrder?.status === "payment_reported"' in business_chat
    assert 'chatCapabilities.can_mark_delivered && currentOrder?.status === "payment_confirmed"' in business_chat

    for source in [business_chat, client_chat, business_support, client_support]:
        assert ".slice(0, 8)" not in source
    assert "Tx hash" not in client_chat
    assert "Identificador de transaccion" not in client_chat
    for source in [client_payment, business_credits]:
        assert "Tx hash" not in source
    assert "Identificador de transaccion" not in client_payment
    assert "Identificador de transaccion" not in business_credits
    assert "Pago exitoso" in business_credits
    assert "Estamos acreditando" in business_credit_presentation
    assert "Copiar ID" not in business_settings
    assert "Copiar identificacion" in business_settings
    back_css = global_css.split(".topbar-back.native-chat-back", 1)[1].split("}", 1)[0]
    assert "0 8px 24px" not in back_css


def test_confirm_payment_in_chat_does_not_require_business_pin_unlock() -> None:
    actions = _read(
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatOrderActions.ts"
    )

    assert 'action === "mark-delivered"' in actions
    assert 'action === "mark-delivered"\n      && !requireUnlockedBusinessPin' in actions
    assert 'action === "confirm-payment"\n      && !requireUnlockedBusinessPin' not in actions
