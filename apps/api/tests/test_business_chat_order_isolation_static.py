from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CHAT_ROOT = ROOT / "apps/web/src/hooks/business-mini-app/chat"
CHAT_FACADE = ROOT / "apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts"
ORDERS_MODEL = ROOT / "apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _chat_source(name: str) -> str:
    return _read(CHAT_ROOT / name)


def _section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


def test_business_chat_uses_order_scoped_session_and_composer_state() -> None:
    session = _chat_source("useBusinessChatSession.ts")
    composer = _chat_source("useBusinessChatComposer.ts")
    attachments = _chat_source("useBusinessChatAttachments.ts")

    assert "chatSessionEpochRef" in session
    assert "isCurrentChatSession" in session
    assert "chatDraftsByOrder" in composer
    assert "chatAttachmentsByOrder" in attachments
    assert "clearSubmittedChatDraft" in composer
    assert "clearSubmittedChatAttachments" in attachments


def test_late_open_and_refresh_responses_cannot_replace_the_active_chat() -> None:
    source = _chat_source("useBusinessChatSession.ts")
    reload_chat = _section(source, "const reloadChatSession", "const openBusinessChat")
    open_chat = _section(source, "const openBusinessChat", "const refreshChatSession")
    refresh_chat = _section(source, "const refreshChatSession", "const refreshChat =")

    assert "targetSessionEpoch" in open_chat
    assert "reloadChatSession(orderId, targetSessionEpoch)" in open_chat
    assert "isCurrentChatSession(orderId, sessionEpoch)" in reload_chat
    assert reload_chat.count("isCurrentChatSession(orderId, sessionEpoch)") >= 2
    assert reload_chat.rindex("isCurrentChatSession(orderId, sessionEpoch)") < reload_chat.index(
        "applyChatThread(orderId, data)"
    )
    assert "targetSessionEpoch" in refresh_chat
    assert "reloadChatSession(targetOrderId, targetSessionEpoch)" in refresh_chat


def test_upload_and_send_completion_are_scoped_to_the_origin_order() -> None:
    attachment_source = _chat_source("useBusinessChatAttachments.ts")
    composer_source = _chat_source("useBusinessChatComposer.ts")
    upload = _section(attachment_source, "const uploadChatAttachment", "const dismissChatAttachmentLink")
    send = _section(composer_source, "const sendChatMessage", "return {")

    for section in (upload, send):
        assert "targetOrderId" in section
        assert "targetSessionEpoch" in section
        assert "isCurrentChatSession(targetOrderId, targetSessionEpoch)" in section

    assert "setChatAttachmentsByOrder" in upload
    assert "clearSubmittedChatDraft(targetOrderId, body)" in send
    assert "clearSubmittedChatAttachments(targetOrderId, attachmentIds)" in send
    assert 'setChatBody("")' not in send
    for section in (upload, send):
        failure = _section(section, "catch (error)", "} finally")
        assert failure.index("isCurrentChatSession(targetOrderId, targetSessionEpoch)") < failure.index(
            "setNotice("
        )
        completion = section.split("} finally", 1)[1]
        assert "chatOrderIdRef.current === targetOrderId" in completion


def test_stale_order_operations_do_not_write_loading_notice_or_financial_state() -> None:
    payment_source = _chat_source("useBusinessPaymentShareActions.ts")
    action_source = _chat_source("useBusinessChatOrderActions.ts")
    payment_details = _section(
        payment_source,
        "const shareConfiguredPaymentDetails",
        "const revealReceiverDetails",
    )
    receiver_details = _section(payment_source, "const revealReceiverDetails", "return {")
    mutation = _section(action_source, "const mutateBusinessChatOrder", "const confirmBusinessPaymentInChat")

    for section in (payment_details, receiver_details, mutation):
        assert "targetSessionEpoch" in section
        assert "isCurrentChatSession(targetOrderId, targetSessionEpoch)" in section

    assert "sharingPaymentDetailsRef.current.has(targetOrderId)" in payment_details
    assert "revealingReceiverDetailsRef.current.has(targetOrderId)" in receiver_details
    assert "businessChatActionRef.current.has(targetOrderId)" in mutation
    assert "chatCapabilitiesOrderIdRef.current !== targetOrderId" in payment_details
    assert "chatCapabilitiesOrderIdRef.current !== targetOrderId" in receiver_details
    assert "chatCapabilitiesOrderIdRef.current !== targetOrderId" in mutation
    assert "routeBusinessPinError" in mutation

    for section in (payment_details, receiver_details, mutation):
        assert "chatOrderIdRef.current === targetOrderId" in section

    payment_failure = _section(payment_details, "catch (error)", "} finally")
    receiver_failure = _section(receiver_details, "catch (error)", "} finally")
    mutation_failure = _section(mutation, "catch (error)", "} finally")
    for failure in (payment_failure, receiver_failure, mutation_failure):
        assert failure.index("isCurrentChatSession(targetOrderId, targetSessionEpoch)") < failure.index(
            "setNotice("
        )


def test_reopening_the_same_order_reflects_only_that_orders_pending_operations() -> None:
    facade = _read(CHAT_FACADE)
    composer = _chat_source("useBusinessChatComposer.ts")
    attachments = _chat_source("useBusinessChatAttachments.ts")
    payment = _chat_source("useBusinessPaymentShareActions.ts")
    actions = _chat_source("useBusinessChatOrderActions.ts")

    assert "composer.activateOrder(orderId)" in facade
    assert "attachments.activateOrder(orderId)" in facade
    assert "paymentShare.activateOrder(orderId)" in facade
    assert "orderActions.activateOrder(orderId)" in facade
    assert "setSendingChatMessage(sendingChatMessageRef.current.has(orderId))" in composer
    assert "setUploadingChatAttachment(uploadingChatAttachmentRef.current.has(orderId))" in attachments
    assert "setSharingPaymentDetails(sharingPaymentDetailsRef.current.has(orderId))" in payment
    assert "setRevealingReceiverDetails(revealingReceiverDetailsRef.current.has(orderId))" in payment
    assert "setBusinessChatAction(businessChatActionRef.current.get(orderId) ?? null)" in actions


def test_business_financial_buttons_remain_capability_and_state_driven() -> None:
    screen_root = ROOT / "apps/web/src/screens/business-app"
    screen = "\n".join(
        _read(path)
        for path in (
            screen_root / "BusinessChatScreen.tsx",
            screen_root / "chat/BusinessChatActionDock.tsx",
            screen_root / "chat/BusinessChatMessageList.tsx",
        )
    )

    assert 'chatCapabilities.can_confirm_payment && currentOrder?.status === "payment_reported"' in screen
    assert 'chatCapabilities.can_mark_delivered && currentOrder?.status === "payment_confirmed"' in screen
    assert "shareConfiguredPaymentDetails" in screen
    assert "revealReceiverDetails" in screen


def test_late_order_detail_cannot_replace_the_order_selected_for_chat_entry() -> None:
    source = _read(ORDERS_MODEL)
    open_order = _section(source, "const openBusinessOrder", "const mutateBusinessOrder")

    assert "businessOrderDetailEpochRef" in source
    assert "businessOrderDetailIdRef" in source
    assert "targetRequestEpoch" in open_order
    assert "isCurrentBusinessOrderDetail(orderId, targetRequestEpoch)" in open_order
    assert open_order.index(
        "isCurrentBusinessOrderDetail(orderId, targetRequestEpoch)"
    ) < open_order.index("setBusinessOrderDetail(data)")


def test_order_detail_mutation_cannot_write_action_state_into_another_order() -> None:
    source = _read(ORDERS_MODEL)
    mutation = _section(source, "const mutateBusinessOrder", "return {")

    assert "businessOrderActionsRef" in source
    assert "targetOrderId" in mutation
    assert "targetRequestEpoch" in mutation
    assert "businessOrderActionsRef.current.has(targetOrderId)" in mutation
    assert "isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)" in mutation
    assert mutation.index(
        "isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)"
    ) < mutation.index("setBusinessOrderDetail(data)")


def test_business_order_list_filters_discard_late_responses_and_keep_last_good_refresh() -> None:
    source = _read(ORDERS_MODEL)
    load_orders = _section(source, "const loadBusinessOrders", "const refreshBusinessOrders")
    refresh_orders = _section(source, "const refreshBusinessOrders", "const syncBusinessOrderFromChat")

    assert "businessOrderListRequestIdRef" in source
    assert "businessOrderFilterRef" in source
    assert "businessOrderRefreshInFlightRef" in source
    assert "targetListRequestId" in load_orders
    assert "previousFilter" in load_orders
    assert "businessOrderListRequestIdRef.current !== targetListRequestId" in load_orders
    assert load_orders.index(
        "businessOrderListRequestIdRef.current !== targetListRequestId"
    ) < load_orders.index("setBusinessOrders(data.items)")
    assert "businessOrderFilterRef.current = previousFilter" in load_orders
    assert 'businessOrderFilterRef.current !== "open"' in refresh_orders
    assert "businessOrderRefreshInFlightRef.current" in refresh_orders
    assert "setBusinessOrders([])" not in refresh_orders
