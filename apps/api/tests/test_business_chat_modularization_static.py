from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CHAT_HOOKS = ROOT / "apps/web/src/hooks/business-mini-app/chat"
CHAT_COMPONENTS = ROOT / "apps/web/src/screens/business-app/chat"
CHAT_FACADE = ROOT / "apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts"
CHAT_SCREEN = ROOT / "apps/web/src/screens/business-app/BusinessChatScreen.tsx"


def test_business_chat_model_is_a_small_facade_over_focused_hooks() -> None:
    expected_hooks = {
        "useBusinessChatSession.ts",
        "useBusinessChatComposer.ts",
        "useBusinessChatAttachments.ts",
        "useBusinessPaymentShareActions.ts",
        "useBusinessChatOrderActions.ts",
    }

    assert CHAT_HOOKS.is_dir()
    assert expected_hooks <= {path.name for path in CHAT_HOOKS.glob("*.ts")}

    facade = CHAT_FACADE.read_text(encoding="utf-8")
    assert len(facade.splitlines()) <= 180
    for hook_name in (
        "useBusinessChatSession",
        "useBusinessChatComposer",
        "useBusinessChatAttachments",
        "useBusinessPaymentShareActions",
        "useBusinessChatOrderActions",
    ):
        assert hook_name in facade

    for api_call in (
        "listOrderMessages",
        "sendOrderMessage",
        "uploadOrderMessageAttachment",
        "revealOrderReceiverDetails",
        "mutateBusinessOrderRequest",
    ):
        assert api_call not in facade


def test_business_chat_screen_composes_focused_visual_components() -> None:
    expected_components = {
        "BusinessChatMessageList.tsx",
        "BusinessChatComposer.tsx",
        "BusinessChatActionDock.tsx",
        "BusinessReceiverDetailsBubble.tsx",
    }

    assert CHAT_COMPONENTS.is_dir()
    assert expected_components <= {path.name for path in CHAT_COMPONENTS.glob("*.tsx")}

    screen = CHAT_SCREEN.read_text(encoding="utf-8")
    assert len(screen.splitlines()) <= 180
    for component_name in (
        "BusinessChatMessageList",
        "BusinessChatComposer",
        "BusinessChatActionDock",
    ):
        assert component_name in screen


def test_business_chat_facade_keeps_the_existing_public_contract() -> None:
    facade = CHAT_FACADE.read_text(encoding="utf-8")
    for public_member in (
        "openBusinessChat",
        "refreshChat",
        "sendChatMessage",
        "uploadChatAttachment",
        "shareConfiguredPaymentDetails",
        "revealReceiverDetails",
        "confirmBusinessPaymentInChat",
        "markBusinessDeliveredInChat",
    ):
        assert public_member in facade
