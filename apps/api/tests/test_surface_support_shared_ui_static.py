from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_client_and_business_support_use_neutral_pure_primitives() -> None:
    shared = _read("apps/web/src/screens/support/SurfaceSupportPrimitives.tsx")
    client = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")
    business = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")

    for component in ("SurfaceSupportInbox", "SurfaceSupportThread", "SurfaceSupportComposer"):
        assert f"export function {component}" in shared
    for component in ("SurfaceSupportInbox", "SurfaceSupportThread"):
        assert component in client
        assert component in business
    assert "<SurfaceSupportComposer" in shared
    for screen in (client, business):
        assert "business-mini-app/helpers" not in screen
        assert "supportStatusLabel" not in screen
        assert "supportCategoryLabel" not in screen
        assert "supportSenderLabel" not in screen
        assert "surface-support" in screen


def test_support_css_has_neutral_surface_contract_and_legacy_chat_compatibility() -> None:
    css = _read("apps/web/src/app/globals.css")
    icons = _read("apps/web/src/components/nodo/ChatComposerIcons.tsx")

    assert ".surface-support" in css
    assert ".surface-support-thread" in css
    assert ".surface-support-ticket-list" in css
    assert "surface-support-icon-svg" in icons
    assert "business-support-icon-svg" in icons
