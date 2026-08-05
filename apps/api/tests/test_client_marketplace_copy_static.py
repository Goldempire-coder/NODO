from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_client_marketplace_copy_describes_registration_without_endorsement() -> None:
    runtime_paths = (
        ROOT / "apps" / "web" / "src" / "screens" / "auth" / "TelegramEntryPage.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientMarketplaceScreens.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientOnboardingScreens.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientWorkspaceShell.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "RemitterScreens.types.ts",
        ROOT / "apps" / "web" / "src" / "constants" / "copy.ts",
        ROOT / "apps" / "api" / "app" / "modules" / "ads" / "marketplace.py",
        ROOT / "apps" / "api" / "app" / "modules" / "orders" / "payment_constants.py",
    )
    runtime_copy = "\n".join(path.read_text(encoding="utf-8") for path in runtime_paths)

    for forbidden in (
        "Busca negocios verificados",
        "negocios verificados por NODO",
        "Negocio verificado",
        "Cambio verificado",
        "Paga directo al negocio verificado",
        "comparar con mas confianza",
    ):
        assert forbidden not in runtime_copy

    for expected in (
        "Busca negocios registrados",
        "Ingresa un monto para ver negocios registrados en NODO.",
        "Compara perfiles registrados en NODO segun tasa, limites y disponibilidad.",
        "Perfil registrado",
        "Paga directamente al negocio seleccionado",
    ):
        assert expected in runtime_copy


def test_visible_runtime_copy_describes_actions_without_safety_promises() -> None:
    runtime_paths = (
        ROOT / "apps" / "web" / "src" / "hooks" / "useTelegramAuth.ts",
        ROOT / "apps" / "web" / "src" / "hooks" / "workspace" / "useClientChatDisputesModel.ts",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "BusinessOrdersScreens.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "BusinessChatScreen.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessChatMessageList.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessReceiverDetailsBubble.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessChatActionDock.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "business-app" / "chat" / "BusinessChatComposer.tsx",
        ROOT / "apps" / "web" / "src" / "constants" / "copy.ts",
        ROOT / "apps" / "api" / "app" / "modules" / "chat" / "service.py",
        ROOT / "apps" / "api" / "app" / "modules" / "admin" / "service.py",
        ROOT / "apps" / "api" / "app" / "modules" / "disputes" / "service_constants.py",
        ROOT / "apps" / "api" / "app" / "modules" / "observability" / "repository.py",
        ROOT / "apps" / "api" / "app" / "core" / "errors.py",
        ROOT / "apps" / "web" / "src" / "hooks" / "business-mini-app" / "useBusinessCreditsModel.ts",
    )
    runtime_copy = "\n".join(path.read_text(encoding="utf-8") for path in runtime_paths)

    for forbidden in (
        "iniciar de forma segura",
        "Pago Movil seguro",
        "compartido de forma segura",
        "datos protegidos",
        "eventos seguros",
        "Pago verificado",
        "hold de creditos de forma segura",
    ):
        assert forbidden not in runtime_copy

    for expected in (
        "iniciar sesion",
        "Pago Movil compartido",
        "datos limitados",
    ):
        assert expected in runtime_copy
