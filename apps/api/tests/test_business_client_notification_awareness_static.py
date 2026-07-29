from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_order_chat_and_support_deep_links_are_handled_by_each_surface() -> None:
    business_model = (ROOT / "apps" / "web" / "src" / "hooks" / "useBusinessMiniAppModel.ts").read_text(encoding="utf-8")
    client_model = (ROOT / "apps" / "web" / "src" / "hooks" / "useClientWorkspaceModel.ts").read_text(encoding="utf-8")

    assert 'deepLinkView === "business-chat"' in business_model
    assert "chat.openBusinessChat(orderId)" in business_model
    assert 'deepLinkView === "business-support"' in business_model
    assert "support.openSupportTicket(ticketId)" in business_model

    assert 'deepLinkView === "order-chat"' in client_model
    assert "openOrderChatRef.current(orderId)" in client_model
    assert 'deepLinkView === "support"' in client_model
    assert "openSupportTicketRef.current(ticketId)" in client_model


def test_surface_attention_polling_is_single_visible_non_overlapping_and_stale_safe() -> None:
    awareness = (
        ROOT / "apps" / "web" / "src" / "hooks" / "useSurfaceAttentionModel.ts"
    ).read_text(encoding="utf-8")
    attention_types = (
        ROOT / "apps" / "web" / "src" / "types" / "notifications.ts"
    ).read_text(encoding="utf-8")

    assert "ATTENTION_REFRESH_INTERVAL_MS = 30_000" in awareness
    assert 'document.visibilityState !== "visible"' in awareness
    assert "refreshInFlightRef.current" in awareness
    assert awareness.count("window.setInterval") == 1
    assert "getSurfaceAttentionSummary(request)" in awareness
    assert "acknowledgeSurfaceAttention(request" in awareness
    assert "/api/v1/notifications/attention-summary" in (
        ROOT / "apps" / "web" / "src" / "api" / "notifications.ts"
    ).read_text(encoding="utf-8")
    assert "/api/v1/notifications/attention/acknowledge" in (
        ROOT / "apps" / "web" / "src" / "api" / "notifications.ts"
    ).read_text(encoding="utf-8")
    assert "attentionStale" in awareness
    assert "acknowledgeAttention" in awareness
    assert "pendingAcknowledgementsRef" not in awareness
    assert "message.body" not in awareness
    assert "storage_path" not in awareness
    assert "signed_url" not in awareness
    assert "resource_id: string" in attention_types
    assert "occurred_at: string" in attention_types
    assert ".resourceId" not in awareness
    assert ".occurredAt" not in awareness


def test_business_and_client_shells_show_actionable_badges_banner_and_stale_state() -> None:
    business_shell = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "screens"
        / "business-app"
        / "BusinessMiniAppShell.tsx"
    ).read_text(encoding="utf-8")
    client_shell = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "screens"
        / "client"
        / "ClientWorkspaceShell.tsx"
    ).read_text(encoding="utf-8")
    business_model = (
        ROOT / "apps" / "web" / "src" / "hooks" / "useBusinessMiniAppModel.ts"
    ).read_text(encoding="utf-8")
    client_model = (
        ROOT / "apps" / "web" / "src" / "hooks" / "useClientWorkspaceModel.ts"
    ).read_text(encoding="utf-8")
    business_orders = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "hooks"
        / "business-mini-app"
        / "useBusinessOrdersModel.ts"
    ).read_text(encoding="utf-8")
    client_orders = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "hooks"
        / "workspace"
        / "useRemitterOrdersModel.ts"
    ).read_text(encoding="utf-8")
    support_model = (
        ROOT / "apps" / "web" / "src" / "hooks" / "useSurfaceSupportModel.ts"
    ).read_text(encoding="utf-8")

    for source in (business_shell, client_shell):
        assert "<AttentionBadge" in source
        assert "<AttentionBanner" in source
        assert "attentionStale" in source

    assert "attentionCounts.orders + attentionCounts.support" not in business_shell
    assert "count={attentionCounts.orders}" in business_shell
    assert "openBusinessOrderWithAttention" in business_model
    assert "openBusinessSupportTicketWithAttention" in business_model
    assert "openClientOrderWithAttention" in client_model
    assert "openClientSupportTicketWithAttention" in client_model
    assert "return true;" in business_orders
    assert "return false;" in business_orders
    assert "return true;" in client_orders
    assert "return false;" in client_orders
    assert "return true;" in support_model
    assert "return false;" in support_model

    business_order_open = business_model.index(
        "const opened = await orders.openBusinessOrder(orderId);"
    )
    business_order_ack = business_model.index(
        'acknowledgeAttention("order", orderId);',
        business_order_open,
    )
    business_support_open = business_model.index(
        "const opened = await support.openSupportTicket(ticketId);"
    )
    business_support_ack = business_model.index(
        'acknowledgeAttention("support", ticketId);',
        business_support_open,
    )
    client_order_open = client_model.index(
        "const opened = await remitterOrders.openOrderDetail(orderId);"
    )
    client_order_ack = client_model.index(
        'acknowledgeAttention("order", orderId);',
        client_order_open,
    )
    client_support_open = client_model.index(
        "const opened = await support.openSupportTicket(ticketId);"
    )
    client_support_ack = client_model.index(
        'acknowledgeAttention("support", ticketId);',
        client_support_open,
    )
    assert business_order_open < business_order_ack
    assert business_support_open < business_support_ack
    assert client_order_open < client_order_ack
    assert client_support_open < client_support_ack


def test_truncated_attention_is_rendered_as_a_non_exact_badge() -> None:
    awareness = (
        ROOT / "apps" / "web" / "src" / "hooks" / "useSurfaceAttentionModel.ts"
    ).read_text(encoding="utf-8")
    component = (
        ROOT / "apps" / "web" / "src" / "components" / "nodo" / "SurfaceAttention.tsx"
    ).read_text(encoding="utf-8")
    business_shell = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "screens"
        / "business-app"
        / "BusinessMiniAppShell.tsx"
    ).read_text(encoding="utf-8")
    client_shell = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "screens"
        / "client"
        / "ClientWorkspaceShell.tsx"
    ).read_text(encoding="utf-8")

    assert "setAttentionTruncated(summary.truncated)" in awareness
    assert "attentionTruncated" in awareness
    assert 'truncated ? "50+"' in component
    assert "truncated={attentionTruncated.orders}" in business_shell
    assert "truncated={attentionTruncated.orders}" in client_shell
    assert "truncated={attentionTruncated.support}" in client_shell


def test_48b2_contract_does_not_claim_durable_message_unread_without_persistence() -> None:
    readme = (
        ROOT
        / "control_plane"
        / "09_SLICES"
        / "slice_48B_business_client_notification_awareness"
        / "README.md"
    ).read_text(encoding="utf-8")
    api_contract = (
        ROOT
        / "control_plane"
        / "09_SLICES"
        / "slice_48B_business_client_notification_awareness"
        / "API_CONTRACT.md"
    ).read_text(encoding="utf-8")

    assert "48B3_IMPLEMENTED_LOCALLY_DURABLE_ATTENTION_READ_STATE" in readme
    assert "POST /api/v1/notifications/attention/acknowledge" in api_contract
    assert "pendientes operativos" in api_contract.lower()
    assert "firma opaca" in api_contract.lower()
    assert "cuerpo del mensaje" not in api_contract.lower().split("## restricciones de privacidad")[0]
