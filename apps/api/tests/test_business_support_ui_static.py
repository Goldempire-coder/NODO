from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_support_filter_change_does_not_trigger_duplicate_load() -> None:
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    business_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    client_screen = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")

    assert "}, [request, setNotice]);" in support_model
    assert 'void loadSupportTickets("active");' in business_screen
    assert "}, [loadSupportTickets]);" in business_screen
    assert "}, [loadSupportTickets, supportFilter]);" not in business_screen
    assert 'void loadSupportTickets("active");' in client_screen
    assert "}, [loadSupportTickets]);" in client_screen
    assert "}, [loadSupportTickets, supportFilter]);" not in client_screen


def test_support_mutations_have_immediate_double_submit_guards() -> None:
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")

    assert "creatingTicketLockRef.current" in support_model
    assert "sendingReplyLockRef.current" in support_model
    assert "openingTicketLockRef.current" in support_model
    assert "if (creatingTicketLockRef.current)" in support_model
    assert "if (sendingReplyLockRef.current)" in support_model


def test_support_reply_draft_is_cleared_only_after_backend_success() -> None:
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    send_position = support_model.index("const payload = await sendSupportMessage")
    clear_position = support_model.index('setSupportReply("")', send_position)
    catch_position = support_model.index("} catch (error) {", send_position)

    assert clear_position < catch_position
    assert 'setSupportReply("")' not in support_model[support_model.index("const submitSupportReply"):send_position]
    assert 'if (selectedSupportTicketRef.current?.id === selectedSupportTicket.id)' in support_model[send_position:catch_position]
    assert "buildOptimisticSupportMessage" not in support_model
    assert "removeSupportMessage" not in support_model


def test_business_support_is_a_single_chat_surface_with_active_archive_buckets() -> None:
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    support_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    assert '"business-support business-support--typing" : "business-support"' in support_screen
    assert 'className="business-card business-support-thread"' not in support_screen
    assert "business-support-composer" in support_screen
    assert "business-support-clip" in support_screen
    assert "PaperclipIcon" in support_screen
    assert "fileInputRef.current?.click()" in support_screen
    assert "business-support-thread-selector" in support_screen
    assert 'aria-label="Ver conversaciones"' in support_screen
    assert "business-support-tabs" not in support_screen
    assert "business-support-ticket-list" in support_screen
    assert "Soporte NODO" in support_screen
    assert "Ayuda para tu negocio" not in support_screen
    assert "Soporte Operativo" not in support_screen
    assert "Volver a conversaciones" not in support_screen
    assert "ArrowLeftIcon" not in support_screen
    assert "business-support__topbar" not in support_screen
    assert "Esperando tu respuesta" in support_screen
    assert "Activas" in support_screen
    assert "Archivadas" in support_screen
    assert 'new Set<SupportTicket["status"]>(["open", "waiting_support", "waiting_user", "escalated"])' in support_model
    assert 'new Set<SupportTicket["status"]>(["resolved", "closed"])' in support_model
    assert ".business-support-composer" in global_css
    assert ".business-support-clip" in global_css
    assert ".business-support-thread-selector" in global_css
    assert ".business-support-inbox__actions" in global_css
    assert ".business-support-new-button" in global_css
    assert ".business-support__topbar" not in global_css
    assert "position: sticky" in global_css
    assert 'className="business-support-new-button"' in support_screen
    assert "Nuevo" in support_screen


def test_business_support_mobile_chat_uses_compact_native_sizing() -> None:
    global_css = _read("apps/web/src/app/globals.css")
    support_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")

    assert "composerFocused" in support_screen
    assert "business-support business-support--typing" in support_screen
    assert "height: min(68dvh, calc(var(--nodo-viewport-height, 100dvh) - 174px), 620px);" in global_css
    assert "max-height: calc(var(--nodo-viewport-height, 100dvh) - 174px);" in global_css
    assert "grid-template-rows: minmax(0, 1fr);" in global_css
    assert ".business-support {\n  height: min(68dvh, calc(var(--nodo-viewport-height, 100dvh) - 174px), 620px);" in global_css
    assert ".business-support-thread {\n  min-height: 0;\n  height: 100%;" in global_css
    assert "overflow: hidden;" in global_css
    assert "overflow-y: auto;" in global_css
    assert "-webkit-overflow-scrolling: touch;" in global_css
    assert "touch-action: pan-y;" in global_css
    assert "min-height: 56px;" in global_css
    assert "width: 34px;" in global_css
    assert "business-support__title" not in global_css
    assert "grid-template-rows: auto minmax(0, 1fr) auto;" in global_css
    assert "font-size: clamp(14px, 3.8vw, 16px);" in global_css
    assert "grid-template-columns: 34px minmax(0, 1fr) auto;" in global_css
    assert "min-height: 36px;" in global_css


def test_business_support_typing_mode_prioritizes_chat_above_mobile_keyboard() -> None:
    support_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    global_css = _read("apps/web/src/app/globals.css")

    assert "focusComposer" in support_screen
    assert "blurComposer" in support_screen
    assert "messagesEndRef.current?.scrollIntoView({ block: \"end\" });" in support_screen
    assert "window.setTimeout(scrollMessagesToEnd, 260);" in support_screen
    assert 'onFocus={focusComposer}' in support_screen
    assert 'onBlur={blurComposer}' in support_screen
    assert "business-shell--keyboard-active" in _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    assert "useMobileKeyboardViewport" in _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    assert "window.visualViewport" in _read("apps/web/src/hooks/useMobileKeyboardViewport.ts")
    assert "--nodo-viewport-height" in global_css
    assert ".app-shell:has(.business-support--typing) .primary-nav" in global_css
    assert ".business-shell--keyboard-active .primary-nav" in global_css
    assert ".primary-nav--hidden" in global_css
    assert "transform: translateY(calc(112% + env(safe-area-inset-bottom)));" in global_css
    assert ".business-support--typing {\n  height: min(72dvh, calc(var(--nodo-viewport-height, 100dvh) - 96px), 640px);" in global_css
    assert ".business-support--typing .business-support__topbar" not in global_css
    assert ".business-support--typing .business-support-thread__summary small" in global_css
    assert ".business-support--typing .business-support-messages" in global_css
    assert ".business-support--typing .business-support-composer__input" in global_css


def test_business_support_prevents_duplicate_active_topic_creation() -> None:
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")

    assert "findMatchingActiveTicket" in support_model
    assert "Ya existe una conversacion activa para este tema." in support_model
    assert "ACTIVE_SUPPORT_STATUSES.has(ticket.status)" in support_model


def test_business_support_new_ticket_transition_is_local_and_does_not_render_inbox() -> None:
    support_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    start_position = support_screen.index("const startNewConversation = () => {")
    end_position = support_screen.index("};", start_position)
    start_handler = support_screen[start_position:end_position]

    assert "loadSupportTickets" not in start_handler
    assert "{!showNewConversation && !selectedSupportTicket ? (" in support_screen
    assert "{!selectedSupportTicket ? (" not in support_screen


def test_business_support_shell_back_returns_from_chat_to_ticket_list() -> None:
    shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")

    assert "handleBusinessBack" in shell
    assert 'view === "business-support" && selectedSupportTicket' in shell
    assert "setSelectedSupportTicket(null)" in shell
    assert 'setSupportReply("")' in shell
    assert 'void loadSupportTickets("active");' in shell
    assert "onClick={handleBusinessBack}" in shell


def test_business_support_upload_picker_and_message_attachment_contract() -> None:
    support_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    support_api = _read("apps/web/src/api/support.ts")
    support_service = _read("apps/api/app/modules/support/service.py")

    assert 'accept="image/*,application/pdf"' in support_screen
    assert "capture=" not in support_screen
    assert "const payload = await uploadSupportAttachment" in support_model
    assert "applySupportMessageResult(current, payload.message, payload.ticket)" in support_model
    assert "Promise<SupportMessageResponse>" in support_api
    assert 'resource_type="support_message"' in support_service
    assert 'body="Adjunto enviado."' in support_service


def test_client_support_creates_general_tickets_without_invalid_order_scope() -> None:
    support_screen = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")

    assert "const startNewConversation = () => {" in support_screen
    assert 'scope: "client_general"' in support_screen
    assert 'void submitSupportTicket({ scope: "client_general" });' in support_screen
    assert 'option value="client_order"' not in support_screen
    assert "Para una orden especifica, abre la orden" in support_screen
    assert 'className="business-support-new-button"' in support_screen
    assert "Nuevo" in support_screen
    assert "Ver tickets" in support_screen
    assert "No tienes tickets archivados." in support_screen
    assert "Este ticket esta archivado." in support_screen
    assert "business-support-clip" in support_screen
    assert 'accept="image/*,application/pdf"' in support_screen
    assert "supportSenderLabel" in support_screen
    assert '"Soporte NODO"' in support_screen


def test_client_support_shell_back_returns_from_ticket_to_ticket_list() -> None:
    shell = _read("apps/web/src/screens/client/ClientWorkspaceShell.tsx")

    assert "handleClientBack" in shell
    assert 'view === "support" && selectedSupportTicket' in shell
    assert "setSelectedSupportTicket(null)" in shell
    assert 'setSupportReply("")' in shell
    assert 'void loadSupportTickets("active");' in shell
    assert "onClick={handleClientBack}" in shell


def test_client_support_request_does_not_depend_on_whole_workspace_state() -> None:
    workspace_model = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")

    assert "const setNotice = state.setNotice;" in workspace_model
    assert "const setClientView = state.setView;" in workspace_model
    assert "[state, token]" not in workspace_model
    assert "[setClientView, setNotice, token]" in workspace_model
