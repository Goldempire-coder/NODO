from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]


def test_public_runtime_copy_uses_neutral_non_custodial_language() -> None:
    paths = [
        ROOT / "apps" / "api" / "app" / "modules" / "orders" / "order_copy.py",
        ROOT / "apps" / "api" / "app" / "modules" / "ads" / "marketplace.py",
        ROOT / "apps" / "api" / "app" / "modules" / "chat" / "service.py",
        ROOT / "apps" / "web" / "src" / "constants" / "copy.ts",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientOnboardingScreens.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientOrderChatScreen.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "BusinessChatScreen.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessChatMessageList.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessReceiverDetailsBubble.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessChatActionDock.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessChatComposer.tsx",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "NODO facilita el contacto entre usuarios y negocios registrados" in source
    assert "Los pagos se realizan directamente entre las partes" in source
    assert "NODO registra la orden y su evidencia" in source
    for forbidden in (
        "NODO organiza el proceso",
        "NODO organiza la orden",
        "negocios verificados por NODO",
        "pago garantizado",
        "fondos protegidos",
        "negocio confiable",
        "avalado por NODO",
    ):
        assert forbidden.lower() not in source.lower()

    for forbidden_word in ("garantizado", "protegido", "seguro", "verificado", "avalado"):
        assert re.search(rf"\b{forbidden_word}\b", source, flags=re.IGNORECASE) is None
    assert "respaldo claro" not in source.lower()
    assert re.search(r"\brespaldo\b", source, flags=re.IGNORECASE) is None


def test_negative_no_guarantee_disclaimer_remains_in_domain_contract() -> None:
    contract = (ROOT / "control_plane" / "03_DOMAIN_RULES" / "ORDER_LIFECYCLE_MASTER.md").read_text(
        encoding="utf-8"
    )

    assert "no recibe, retiene, transfiere ni garantiza" in contract.lower()
