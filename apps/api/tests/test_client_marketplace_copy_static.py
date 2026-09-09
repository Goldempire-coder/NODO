from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_client_marketplace_copy_describes_registration_without_endorsement() -> None:
    runtime_paths = (
        ROOT / "apps" / "web" / "src" / "screens" / "auth" / "TelegramEntryPage.tsx",
        ROOT / "apps" / "web" / "src" / "hooks" / "useTelegramAuth.ts",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientMarketplaceScreens.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientOnboardingScreens.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientWorkspaceShell.tsx",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "RemitterScreens.types.ts",
        ROOT / "apps" / "web" / "src" / "screens" / "client" / "chat" / "ClientReceiverDetailsBubble.tsx",
        ROOT / "apps" / "web" / "src" / "constants" / "paymentLabels.ts",
        ROOT / "apps" / "web" / "src" / "constants" / "copy.ts",
        ROOT / "apps" / "api" / "app" / "modules" / "ads" / "marketplace.py",
        ROOT / "apps" / "api" / "app" / "modules" / "orders" / "payment_constants.py",
        ROOT / "apps" / "api" / "app" / "routes" / "telegram_bot.py",
        ROOT / "scripts" / "build_telegram_welcome_image.py",
    )
    runtime_copy = "\n".join(path.read_text(encoding="utf-8") for path in runtime_paths)

    for forbidden in (
        "Busca negocios verificados",
        "negocios verificados por NODO",
        "Negocio verificado",
        "negocio verificado",
        "Cambio verificado",
        "Paga directo al negocio verificado",
        "comparar con mas confianza",
        "Listo para cambiar",
        "Indica cuÃ¡nto quieres cambiar.",
        "Conecta con negocios verificados para cambiar",
        "Acuerda los detalles dentro de NODO.",
        "Tu confianza comienza",
        "con negocios verificados.",
        "+58 412 000 0000",
        "0414 1234567 o +58 414 1234567",
        "¿Cuánto quieres cambiar?",
        "Antes de cambiar",
        "Tu familiar recibe",
        "somos casa de cambio",
        "casa de cambio",
        "escrow",
        "dinero protegido",
        "fondos garantizados",
        "garantizamos transacciones",
        "Elige un negocio registrado.",
        "Negocios que publican en NODO",
        "Ingresa un monto para ver negocios que publican en NODO.",
        "NODO revisa datos del negocio antes de publicarlo.",
    ):
        assert forbidden not in runtime_copy

    for expected in (
        "Directorio de ofertas",
        "¿Qué monto buscas?",
        "Ofertas disponibles",
        "Ingresa un monto para ver ofertas disponibles.",
        "Revisa monto, condiciones y disponibilidad.",
        "Cada negocio publica sus datos.",
        "Perfil registrado",
        "Usa solo los datos publicados por el negocio en esta orden.",
        "NODO no recibe, retiene, transfiere ni garantiza fondos",
        "NODO muestra ofertas de negocios registrados",
        "Las condiciones se coordinan directamente entre cliente y negocio.",
        "Listo para usar NODO",
        "Entrega publicada:",
        "Escribe tu numero completo",
        "Puede ser de Venezuela, Estados Unidos u otro pais.",
        "Escribe el numero completo",
        "Compara ofertas publicadas, revisa sus condiciones y crea tu orden en pocos pasos.",
        "Indica el monto que buscas.",
        "Elige una oferta disponible.",
        "Revisa los datos publicados por el negocio.",
        "Guarda la evidencia de tu orden.",
        "NODO registra tu orden",
        "y conserva evidencia.",
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


def test_telegram_welcome_and_client_phone_copy_are_country_neutral() -> None:
    onboarding = (ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientOnboardingScreens.tsx").read_text(encoding="utf-8")
    receiver_details = (ROOT / "apps" / "web" / "src" / "screens" / "client" / "chat" / "ClientReceiverDetailsBubble.tsx").read_text(encoding="utf-8")
    welcome_image_source = (ROOT / "scripts" / "build_telegram_welcome_image.py").read_text(encoding="utf-8")
    bot_route = (ROOT / "apps" / "api" / "app" / "routes" / "telegram_bot.py").read_text(encoding="utf-8")
    combined = "\n".join((onboarding, receiver_details, welcome_image_source, bot_route))

    for forbidden in (
        "+58 412 000 0000",
        "0414 1234567 o +58 414 1234567",
        "Indica cu\u00e1nto quieres cambiar.",
        "Conecta con negocios verificados para cambiar",
        "Acuerda los detalles dentro de NODO.",
        "Tu confianza comienza",
        "con negocios verificados.",
        "Seguro",
        "R\u00e1pido",
        "Confiable",
        "Elige un negocio registrado.",
    ):
        assert forbidden not in combined

    for expected in (
        "Escribe tu numero completo",
        "Puede ser de Venezuela, Estados Unidos u otro pais.",
        "Escribe el numero completo",
        "Compara ofertas publicadas, revisa sus condiciones y crea tu orden en pocos pasos.",
        "Indica el monto que buscas.",
        "Elige una oferta disponible.",
        "Revisa los datos publicados por el negocio.",
        "Guarda la evidencia de tu orden.",
        "NODO registra tu orden",
        "y conserva evidencia.",
        "Abre NODO desde el menu de Telegram para comenzar.",
    ):
        assert expected in combined


def test_client_marketplace_mobile_copy_cannot_force_horizontal_overflow() -> None:
    marketplace = (ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientMarketplaceScreens.tsx").read_text(encoding="utf-8")
    css = (ROOT / "apps" / "web" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "Ofertas disponibles" in marketplace
    assert "Negocios que publican en NODO" not in marketplace
    assert ".business-shell" in css
    assert "overflow-x: clip;" in css
    assert ".marketplace-home" in css
    assert ".business-shell__title" in css
    assert ".exchange-card__title" in css
    assert "overflow-wrap: anywhere;" in css
    assert "min-width: 0;" in css


def test_backend_chat_system_copy_uses_neutral_order_language() -> None:
    chat_service = (ROOT / "apps" / "api" / "app" / "modules" / "chat" / "service.py").read_text(encoding="utf-8")

    for forbidden in (
        "Negociacion creada",
        "No envies el pago",
        "Cliente marco Pago enviado",
        "Negocio marco Pago Movil enviado",
        "Negocio marco entrega enviada",
        "Negociacion completada",
        "antes de enviar",
    ):
        assert forbidden not in chat_service

    for expected in (
        "Solicitud abierta",
        "No realices ningun pago directo",
        "Cliente reporto un pago directo",
        "Negocio verifico ingreso reportado",
        "Negocio marco la entrega acordada como realizada",
        "Orden completada",
        "antes de realizar cualquier pago directo",
    ):
        assert expected in chat_service
