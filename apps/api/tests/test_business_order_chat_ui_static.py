from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_business_order_chat_uses_native_chat_surface_not_table_rows() -> None:
    chat_screen = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    assert "business-order-chat" in chat_screen
    assert "business-order-chat-messages" in chat_screen
    assert "business-order-chat-message business-order-chat-message--mine" in chat_screen
    assert "business-order-chat-composer" in chat_screen
    assert "business-order-chat-composer__input" in chat_screen
    assert "business-order-chat-actions" in chat_screen
    assert "business-list" not in chat_screen
    assert "business-row ad-row" not in chat_screen
    assert "Chat con cliente" in chat_screen
    assert ".business-order-chat {" in global_css
    assert ".business-order-chat-messages {" in global_css
    assert ".business-order-chat-composer {" in global_css
    assert "overflow-y: auto;" in global_css
    assert "grid-template-rows: auto minmax(0, 1fr) auto;" in global_css


def test_business_order_chat_has_compact_attachment_and_keyboard_safe_typing_mode() -> None:
    chat_screen = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    assert "PaperclipIcon" in chat_screen
    assert "fileInputRef.current?.click()" in chat_screen
    assert 'accept="image/*,application/pdf"' in chat_screen
    assert 'aria-label="Adjuntar comprobante o soporte"' in chat_screen
    assert "composerFocused ? \"business-order-chat business-order-chat--typing\"" in chat_screen
    assert "focusComposer" in chat_screen
    assert "blurComposer" in chat_screen
    assert "window.setTimeout(scrollMessagesToEnd, 260);" in chat_screen
    assert "business-shell--keyboard-active" in _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    assert "useMobileKeyboardViewport" in _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    assert "window.visualViewport" in _read("apps/web/src/hooks/useMobileKeyboardViewport.ts")
    assert "--nodo-viewport-height" in global_css
    assert ".app-shell:has(.business-order-chat--typing) .primary-nav" in global_css
    assert ".business-shell--keyboard-active .primary-nav" in global_css
    assert ".primary-nav--hidden" in global_css
    assert ".business-order-chat--typing {" in global_css
    assert ".business-order-chat--typing > .business-order-chat-actions" in global_css
    assert ".business-order-chat--typing .business-order-chat-composer" in global_css
    assert "grid-template-columns: 34px minmax(0, 1fr) 74px;" in global_css
    assert "-webkit-overflow-scrolling: touch;" in global_css
    assert "touch-action: pan-y;" in global_css
    assert "business-order-chat__compact-code" in chat_screen
    assert "business-order-chat-attachment__button" in chat_screen
    assert "openChatAttachment" in chat_screen
    assert "Adjunto privado" not in chat_screen


def test_business_order_chat_refreshes_silently_and_prevents_duplicate_mutations() -> None:
    chat_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    chat_screen = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    chat_types = _read("apps/web/src/types/chat.ts")
    app_model = _read("apps/web/src/hooks/useBusinessMiniAppModel.ts")

    assert "BUSINESS_ORDER_CHAT_REFRESH_MS = 5000" in chat_screen
    assert "void refreshChat({ silent: true });" in chat_screen
    assert 'model.view !== "business-chat"' in chat_screen
    assert 'document.visibilityState !== "visible"' in chat_screen
    assert "const refreshChat = useCallback(async (options?: { silent?: boolean })" in chat_model
    assert "if (!options?.silent)" in chat_model
    assert "listOrderMessages<ChatThread<BusinessOrderSummary>>(request, orderId, 50)" in chat_model
    assert "listOrderMessages<ChatThread<BusinessOrderSummary>>(request, targetOrderId, 50)" in chat_model
    assert "refreshingChatRef.current" in chat_model
    assert "chatOrderIdRef.current !== targetOrderId" in chat_model
    assert "sendingChatMessageRef.current" in chat_model
    assert "uploadingChatAttachmentRef.current" in chat_model
    assert "openingOrderDisputeRef.current" in chat_model
    assert "syncBusinessOrderFromChat(data.order)" in chat_model
    assert "ChatThread<BusinessOrderSummary>" in chat_model
    assert "order: TOrder" in chat_types
    assert "syncBusinessOrderFromChat: orders.syncBusinessOrderFromChat" in app_model
    assert "const body = chatBody.trim();" in chat_model
    assert "(!body && chatAttachments.length === 0)" in chat_model
    assert 'setChatBody("")' in chat_model
    refresh_source = chat_model.split("const refreshChat", 1)[1].split(
        "const uploadChatAttachment", 1
    )[0]
    refresh_catch = refresh_source.split("catch (error)", 1)[1].split(
        "} finally", 1
    )[0]
    assert "setChatMessages(" not in refresh_catch
    assert "setChatCapabilities(" not in refresh_catch


def test_order_chat_suppresses_global_attention_and_success_toasts_while_open() -> None:
    business_shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    client_shell = _read("apps/web/src/screens/client/ClientWorkspaceShell.tsx")
    business_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    client_model = _read("apps/web/src/hooks/workspace/useClientChatDisputesModel.ts")
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")

    assert 'view === "business-chat"' in business_shell
    assert "attentionBannerItem" in business_shell
    assert "item={attentionBannerItem}" in business_shell
    assert 'view === "order-chat"' in client_shell
    assert "attentionBannerItem" in client_shell
    assert "item={attentionBannerItem}" in client_shell
    assert 'setNotice("Mensaje enviado.")' not in business_model
    assert 'setNotice("Mensaje registrado.")' not in client_model
    assert "business-order-chat__compact-code" in client_chat
    assert "business-order-chat-attachment__button" in client_chat
    assert "openChatAttachment" in client_chat
    assert "Adjunto privado" not in client_chat


def test_order_chat_keeps_visible_attachment_fallback_for_telegram_webview() -> None:
    business_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    business_chat = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    client_model = _read("apps/web/src/hooks/workspace/useClientChatDisputesModel.ts")
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
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
    business_chat = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    client_chat = _read("apps/web/src/screens/client/ClientOrderChatScreen.tsx")
    business_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")

    assert "const [chatOrder, setChatOrder]" in business_model
    assert "setChatOrder(data.order)" in business_model
    assert "chatOrder?.id === chatOrderId" in business_chat
    for source in [business_chat, client_chat]:
        assert 'status === "cancelled"' in source
        assert 'status === "completed"' in source
        assert "Esta negociacion esta cerrada." in source
        assert "!chatIsTerminal ? (" in source
        assert "business-order-chat-composer" in source
