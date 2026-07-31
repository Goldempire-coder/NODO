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
    assert "grid-template-rows: auto minmax(0, 1fr) auto auto auto;" in global_css


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
    assert ".business-order-chat--typing .business-order-chat-actions" in global_css
    assert ".business-order-chat--typing .business-order-chat-composer" in global_css
    assert "grid-template-columns: 34px minmax(0, 1fr) 74px;" in global_css
    assert "-webkit-overflow-scrolling: touch;" in global_css
    assert "touch-action: pan-y;" in global_css


def test_business_order_chat_refreshes_silently_and_prevents_duplicate_mutations() -> None:
    chat_model = _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    chat_screen = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")

    assert "BUSINESS_ORDER_CHAT_REFRESH_MS = 5000" in chat_screen
    assert "void refreshChat({ silent: true });" in chat_screen
    assert 'model.view !== "business-chat"' in chat_screen
    assert 'document.visibilityState !== "visible"' in chat_screen
    assert "const refreshChat = useCallback(async (options?: { silent?: boolean })" in chat_model
    assert "if (!options?.silent)" in chat_model
    assert "listOrderMessages<ChatThread>(request, orderId, 50)" in chat_model
    assert "listOrderMessages<ChatThread>(request, targetOrderId, 50)" in chat_model
    assert "refreshingChatRef.current" in chat_model
    assert "chatOrderIdRef.current !== targetOrderId" in chat_model
    assert "sendingChatMessageRef.current" in chat_model
    assert "uploadingChatAttachmentRef.current" in chat_model
    assert "openingOrderDisputeRef.current" in chat_model
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
