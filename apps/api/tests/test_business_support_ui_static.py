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

    assert 'className="business-support"' in support_screen
    assert 'className="business-card business-support-thread"' not in support_screen
    assert "business-support-composer" in support_screen
    assert "business-support-ticket-list" in support_screen
    assert "Soporte NODO" in support_screen
    assert "Esperando tu respuesta" in support_screen
    assert "Activas" in support_screen
    assert "Archivadas" in support_screen
    assert 'new Set<SupportTicket["status"]>(["open", "waiting_support", "waiting_user", "escalated"])' in support_model
    assert 'new Set<SupportTicket["status"]>(["resolved", "closed"])' in support_model
    assert ".business-support-composer" in global_css
    assert "position: sticky" in global_css


def test_business_support_prevents_duplicate_active_topic_creation() -> None:
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")

    assert "findMatchingActiveTicket" in support_model
    assert "Ya existe una conversacion activa para este tema." in support_model
    assert "ACTIVE_SUPPORT_STATUSES.has(ticket.status)" in support_model


def test_client_support_request_does_not_depend_on_whole_workspace_state() -> None:
    workspace_model = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")

    assert "const setNotice = state.setNotice;" in workspace_model
    assert "const setClientView = state.setView;" in workspace_model
    assert "[state, token]" not in workspace_model
    assert "[setClientView, setNotice, token]" in workspace_model
