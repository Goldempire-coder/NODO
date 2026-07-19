from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_frontend_telegram_auth_persists_refresh_session_for_lifecycle() -> None:
    auth_types = _read("apps/web/src/types/auth.ts")
    telegram_hook = _read("apps/web/src/hooks/useTelegramAuth.ts")
    telegram_entry = _read("apps/web/src/screens/auth/TelegramEntryPage.tsx")
    auth_api = _read("apps/web/src/api/auth.ts")
    api_client = _read("apps/web/src/api/client.ts")
    session_helper = _read("apps/web/src/api/session.ts")
    telemetry = _read("apps/web/src/observability/clientTelemetry.ts")

    assert "refresh_token: string" in auth_types
    assert 'writeAuthSession("telegram"' in telegram_hook
    assert "readAuthSession" in telegram_hook
    assert "refreshAuthSession" in telegram_hook
    assert "canUseStoredSession" in telegram_hook
    assert "auth-2026071502" in telegram_hook
    assert "notifyTelegram" in telegram_hook
    assert "function wait(ms: number)" in telegram_hook
    assert "for (let attempt = 1; attempt <= 3; attempt += 1)" in telegram_hook
    assert "Conectando con NODO..." in telegram_hook
    assert "Codigo ${code}" in telegram_hook
    assert "Cierra y abre desde el boton nuevo." in telegram_hook
    assert 'surface === "business" ? "business_mini_app" : "client_mini_app"' in telegram_entry
    assert '"Content-Type": "text/plain;charset=UTF-8"' in auth_api
    assert "JSON.stringify({ init_data: initData, surface })" in auth_api
    assert '"X-NODO-Surface": surface' not in auth_api
    assert "refreshAuthSession(surface)" in api_client
    assert "buildObservedRequest" in api_client
    assert "emitApiFailure" in api_client
    assert "X-Correlation-Id" in telemetry
    assert "X-NODO-Operation-Id" in telemetry
    assert "requestSurface(path, headers)" in telemetry
    assert "nodo_observability_correlation_id" in telemetry
    assert "const refreshPromises" in session_helper
    assert "/api/v1/auth/refresh" in session_helper
    assert "function canUseSessionStorage()" in session_helper
    assert "try {" in session_helper
    assert "window.sessionStorage.setItem" in session_helper
    assert "localStorage" not in session_helper


def test_admin_web_does_not_import_telegram_runtime_and_can_use_refresh_payload() -> None:
    admin_entry = _read("apps/web/src/screens/auth/AdminWebEntryPage.tsx")
    admin_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    admin_users_model = _read("apps/web/src/hooks/admin-web/useAdminUsersModel.ts")
    admin_users_screen = _read("apps/web/src/screens/admin-web/AdminUserScreens.tsx")
    admin_businesses_model = _read("apps/web/src/hooks/admin-web/useAdminBusinessesModel.ts")

    assert "telegramTheme" not in admin_entry
    assert "@telegram-apps" not in admin_entry
    assert "refresh_token" in admin_entry
    assert "if (submittedSession.refreshToken)" in admin_entry
    assert "const validatedSession = readAuthSession(\"admin\")" in admin_entry
    assert "setSession({ token: validatedSession.accessToken, user })" in admin_entry
    assert '"X-NODO-Surface": "admin_web"' in admin_model
    assert '{ view: "businesses" as const, label: "Negocios", action: () => businessIntake.loadBusinesses("") }' in admin_model
    assert '{ view: "users" as const, label: "Clientes", action: () => users.loadUsers() }' in admin_model
    assert 'const [businessFilter, setBusinessFilter] = useState("")' in admin_businesses_model
    assert 'role: "remitter"' in admin_users_model
    assert "A-10 Clientes" in admin_users_screen
    assert "Los negocios se gestionan en Negocios." in admin_users_screen
    assert "business_owner" not in admin_users_screen


def test_admin_business_intake_defaults_to_active_submissions_for_real_flow_review() -> None:
    admin_api = _read("apps/web/src/api/admin.ts")
    admin_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    intake_model = _read("apps/web/src/hooks/admin-web/useAdminBusinessIntakesModel.ts")
    intake_screen = _read("apps/web/src/screens/admin-web/AdminBusinessIntakeScreens.tsx")

    assert 'const [intakeFilter, setIntakeFilter] = useState("submitted")' in intake_model
    assert "const normalizedStatus = status.trim().toLowerCase() || \"submitted\"" in intake_model
    assert 'businessIntake.loadBusinessIntakes("submitted")' in admin_model
    assert "pending_business_intakes" in admin_model
    assert "overview.refreshDashboardSnapshot()" in admin_model
    assert "window.setInterval" in admin_model
    assert "openBusinessIntakeDocument: businessIntake.openBusinessIntakeDocument" in admin_model
    assert 'normalizedStatus !== "all" ? normalizedStatus : undefined' in admin_api
    assert "getAdminBusinessIntakeDocumentViewUrl" in admin_api
    assert "Todas" not in intake_screen
    assert "Aceptadas" not in intake_screen
    assert "En revision" in intake_screen
    assert "Borradores" in intake_screen
    assert "Checklist para aprobar" in intake_screen
    assert 'openBusinessIntakeDocument(file.id, "view")' in intake_screen
    assert "Descargar" in intake_screen
    assert "Nota interna opcional" in intake_screen
    assert "Motivo para aprobar o rechazar" not in intake_screen
    assert "Completar ficha manualmente" in intake_screen
    assert "Codigo invitacion" in intake_screen
    assert "Cedula responsable" in intake_screen
    assert "RIF negocio" in intake_screen
    assert "Limite diario" in intake_screen
    assert "Montos autorizados" in intake_screen
    assert "Rango declarado" not in intake_screen
    assert "Borrar y reiniciar onboarding" in intake_screen
    assert "Guardar y poner en revision" in intake_screen
    assert "Crear negocio pendiente" in intake_screen
    assert "Lista para revision admin" in intake_screen
    assert "Esta pantalla sirve para decidir" in intake_screen
    assert "documentKindLabel" in intake_screen
    assert "Faltan datos para aprobar" in intake_screen
    assert "saveBusinessIntakeManual" in admin_model
    assert "updateAdminBusinessIntake" in admin_api
    assert "requiresReason: false" in intake_model
    assert "download_filename" in intake_model
    assert "queueCriticalAction" not in intake_model.split("const openBusinessIntakeDocument", 1)[1].split("const saveBusinessIntakeManual", 1)[0]
    assert "Escribe un motivo de revision antes de ver o descargar documentos." not in intake_model
    assert "No hay solicitudes activas en este filtro." in intake_screen
    assert "Intake muestra negocios que estan intentando entrar" in intake_screen
    admin_css = _read("apps/web/src/app/admin-web.css")
    assert "cursor: not-allowed" not in admin_css
    assert "button:not(:disabled):hover" in admin_css


def test_business_mini_app_uses_surface_session_gate_not_businesses_me_gate() -> None:
    business_model = _read("apps/web/src/hooks/useBusinessMiniAppModel.ts")
    access_model = _read("apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts")
    payment_methods_model = _read("apps/web/src/hooks/business-mini-app/useBusinessPaymentMethodsModel.ts")
    availability_model = _read("apps/web/src/hooks/business-mini-app/useBusinessAvailabilityModel.ts")
    home_summary_model = _read("apps/web/src/hooks/business-mini-app/useBusinessHomeSummaryModel.ts")
    pin_guards = _read("apps/web/src/hooks/business-mini-app/businessPinGuards.ts")
    business_shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    business_views = _read("apps/web/src/constants/businessViews.ts")
    business_screens = _read("apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx")
    business_dashboard = _read("apps/web/src/screens/business-app/BusinessDashboardScreen.tsx")
    ads_model = _read("apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts")
    credits_model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    credits_screen = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    orders_model = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    orders_screen = _read("apps/web/src/screens/business-app/BusinessOrdersScreens.tsx")
    chat_screen = _read("apps/web/src/screens/business-app/BusinessChatScreen.tsx")
    support_screen = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")
    credits_api = _read("apps/web/src/api/credits.ts")
    surface_api = _read("apps/web/src/api/surface.ts")

    assert "useBusinessAccessModel" in business_model
    assert "acceptBusinessTerms" in business_model
    assert "TERMS_ACCEPTANCE_REQUIRED" in business_model
    assert "hasAcceptedCurrentClientTerms" in business_model
    assert '"business-terms"' in business_views
    assert "BusinessTermsScreen" in business_screens
    assert "termsRequired" in business_shell
    assert "canUseBusinessNav" in business_shell
    assert "useBusinessHomeSummaryModel" in business_model
    assert '"X-NODO-Surface", "business_mini_app"' in business_model
    assert "useBusinessAccessModel({ request, setBusy, setNotice, setView })" in business_model
    assert "BUSINESS_PIN_REQUIRED" in pin_guards
    assert "requireUnlockedBusinessPin" in pin_guards
    assert "routeBusinessPinError" in access_model
    assert "routeBusinessPinError" in ads_model
    assert "routeBusinessPinError" in credits_model
    assert "handleBusinessPinError" in access_model
    assert 'setView("business-pin")' in pin_guards
    assert "pendingPaymentMethodDeleteId" in payment_methods_model
    assert "deletingPaymentMethodId" in payment_methods_model
    assert "queuePaymentMethodDeleteUntilPin" in payment_methods_model
    assert "deletePaymentMethodUnlocked" in payment_methods_model
    assert "await paymentMethods.deletePaymentMethodUnlocked(pendingDeleteId)" in access_model
    assert "await paymentMethods.loadPaymentMethods()" in access_model
    assert "refreshCreditWallet: credits.refreshCreditWallet" in business_model
    assert "const loadHomeSummary = useCallback" not in business_model
    assert "view !== \"business-dashboard\"" not in business_model
    assert "const loadHomeSummary = useCallback" in home_summary_model
    assert "view !== \"business-dashboard\"" in home_summary_model
    assert "runHomeSummaryRefresh" in home_summary_model
    assert "refreshCreditWallet" in home_summary_model
    assert "refreshMyAds" in home_summary_model
    assert "refreshBusinessOrders" in home_summary_model
    assert "loadHomeSummary" in business_shell
    assert "onClick={openHome}" in business_shell
    assert "homeCreditWallet" not in business_dashboard
    assert "void refreshCreditWallet().then" not in business_dashboard
    assert "isRefreshing" in business_dashboard
    assert "blocked_credits" in business_dashboard
    assert "consumed_credits" in business_dashboard
    assert "Zelle / USDT" in business_dashboard
    assert 'cache: "no-store"' in credits_api
    assert "getBusinessSurfaceSession" in access_model
    assert "const openHome = () =>" in business_shell
    assert 'if (view === "business-dashboard")' not in business_shell
    assert 'if (busy || view === "business-dashboard")' not in business_shell
    assert 'if (busy || view === "my-ads")' not in business_shell
    assert 'setLoadingScreen("my-ads")' in ads_model
    assert "generatingCreditPayment" in credits_model
    assert '"credits-ledger"' not in business_views
    assert '"credits-ledger"' not in business_shell
    assert "CreditsLedgerScreen" not in business_screens
    assert "loadCreditLedger" not in credits_model
    assert "creditLedger" not in credits_model
    assert "listBusinessCreditLedger" not in credits_api
    assert "Movimientos" not in credits_screen
    assert "Historial de creditos" not in credits_screen
    assert "Comprar" in credits_screen
    assert "Referidos" in credits_screen
    assert 'onClick={() => void loadReferrals()}>Referidos</Button>' not in credits_screen
    assert "Copiar wallet" in credits_screen
    assert "Wallet copiada." in credits_screen
    assert "payment-step-grid" in credits_screen
    assert "Red Base" in credits_screen
    assert "red BASE" not in credits_screen
    assert "red BASE" not in credits_model
    assert 'recordBusinessActionStarted("credit_payment_create"' in credits_model
    assert 'recordBusinessActionStarted("credit_tx_submit"' in credits_model
    assert "refreshingCreditPurchase" in credits_model
    assert "verifyingCreditTx" in credits_model
    assert "businessOrderAction" in orders_model
    assert "pollBusinessOrderUpdates" in orders_model
    assert "businessOrdersWatchReadyRef" in orders_model
    assert "Nueva orden ${newOrder.public_order_code}" in orders_model
    assert "Pago reportado en ${updatedOrder.public_order_code}" in orders_model
    assert 'notifyTelegram("success")' in orders_model
    assert "orders.pollBusinessOrderUpdates()" in business_model
    assert "window.setInterval" in business_model
    assert 'recordBusinessActionStarted(telemetryAction, "business-order-detail")' in orders_model
    assert "business_order_confirm_payment" in orders_model
    assert "business_order_reject_payment_report" in orders_model
    assert "business_order_mark_delivered" in orders_model
    assert "sendingChatMessage" in _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    assert "uploadingChatAttachment" in _read("apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts")
    assert "creatingSupportTicket" in _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    assert "sendingSupportReply" in _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    assert "business_availability_" in availability_model
    assert "pendingAvailabilityTarget" in availability_model
    assert "Idempotency-Key" in _read("apps/web/src/api/businesses.ts")
    assert "disabled={busy || !baseUsdcTxHash.trim()}" not in credits_screen
    assert "disabled={verifyingCreditTx || !baseUsdcTxHash.trim()}" in credits_screen
    assert "Verificando..." in credits_screen
    assert "Actualizando..." in credits_screen
    assert "disabled={businessOrderAction === \"confirm-payment\"" in orders_screen
    assert "Confirmando..." in orders_screen
    assert "Rechazando..." in orders_screen
    assert "Marcando..." in orders_screen
    assert "disabled={busy || !chatCapabilities.can_send_message" not in chat_screen
    assert "sendingChatMessage" in chat_screen
    assert "uploadingChatAttachment" in chat_screen
    assert "openingOrderDispute" in chat_screen
    assert "disabled={busy || supportForm.subject" not in support_screen
    assert "creatingSupportTicket" in support_screen
    assert "sendingSupportReply" in support_screen
    assert "uploadingSupportAttachment" in support_screen
    assert 'setView("business-orders");\n    setBusy(true);' in orders_model
    assert "/api/v1/surface/session" in surface_api
    assert "/api/v1/businesses/me" not in business_model
    assert "/api/v1/businesses/me" not in access_model


def test_static_web_build_injects_public_api_env_values() -> None:
    next_config = _read("apps/web/next.config.mjs")

    assert 'env: {' in next_config
    assert 'NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? ""' in next_config
    assert 'NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL ?? ""' in next_config
    assert 'NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED: process.env.NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED ?? ""' in next_config


def test_frontend_observability_is_separated_and_redacts_sensitive_metadata() -> None:
    api_client = _read("apps/web/src/api/client.ts")
    telemetry = _read("apps/web/src/observability/clientTelemetry.ts")
    business_shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    public_env = _read("apps/web/src/lib/env.ts")

    assert "const CORRELATION_STORAGE_KEY" not in api_client
    assert "buildObservedRequest" in telemetry
    assert "emitApiFailure" in telemetry
    assert "recordScreenView" in telemetry
    assert "recentBreadcrumbs" in telemetry
    assert "OBSERVABILITY_ENDPOINT = \"/api/v1/observability/events\"" in telemetry
    assert "safeMetadata" in telemetry
    assert '"pin"' in telemetry
    assert '"wallet"' in telemetry
    assert '"zelle"' in telemetry
    assert '"token"' in telemetry
    assert '"account"' in telemetry
    assert '"storage"' in telemetry
    assert "recordSlowScreenTransition(view, previousView, elapsedMs(viewStartedAtRef.current))" in business_shell
    assert "recordScreenView(view, previousView)" in business_shell
    assert "previousViewRef.current = view" in business_shell
    assert "NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED" in public_env
    assert "recordSlowSensitiveAction" in telemetry
    assert "slow_sensitive_action" in telemetry
    assert "slow_screen_transition" in telemetry
    assert "recordActionBreadcrumb" in _read("apps/web/src/hooks/actionTelemetry.ts")


def test_client_mini_app_has_action_scoped_state_and_safe_breadcrumbs() -> None:
    client_model = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")
    client_state = _read("apps/web/src/hooks/workspace/useClientWorkspaceState.ts")
    marketplace_model = _read("apps/web/src/hooks/workspace/useClientMarketplaceModel.ts")
    orders_model = _read("apps/web/src/hooks/workspace/useRemitterOrdersModel.ts")
    payment_model = _read("apps/web/src/hooks/workspace/usePaymentReportModel.ts")
    chat_model = _read("apps/web/src/hooks/workspace/useClientChatDisputesModel.ts")
    support_model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")
    marketplace_screen = _read("apps/web/src/screens/client/ClientMarketplaceScreens.tsx")
    order_screen = _read("apps/web/src/screens/client/ClientOrderScreens.tsx")
    payment_screen = _read("apps/web/src/screens/client/ClientPaymentScreens.tsx")
    chat_screen = _read("apps/web/src/screens/client/ClientScreens.tsx")
    support_screen = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")
    remitter_types = _read("apps/web/src/screens/client/RemitterScreens.types.ts")
    telemetry_helper = _read("apps/web/src/hooks/actionTelemetry.ts")

    assert "searchingMarketplace" in client_state
    assert "creatingOrder" in client_state
    assert "loadingPaymentInstructions" in client_state
    assert "uploadingPaymentEvidence" in client_state
    assert "submittingPaymentReport" in client_state
    assert "sendingChatMessage" in client_state
    assert "openingOrderDispute" in client_state
    assert "mainActionBusy = state.busy || state.creatingOrder || state.submittingPaymentReport" in client_model
    assert "searchingMarketplace: state.searchingMarketplace" in client_model
    assert "creatingOrder: state.creatingOrder" in client_model
    assert "submittingPaymentReport: state.submittingPaymentReport" in client_model
    assert "sendingChatMessage: state.sendingChatMessage" in client_model
    assert "creatingSupportTicket: support.creatingSupportTicket" in client_model
    assert 'recordActionStarted("client_marketplace_search"' in marketplace_model
    assert 'recordActionStarted("client_order_create"' in orders_model
    assert 'recordActionStarted("client_order_cancel"' in orders_model
    assert 'recordActionStarted("client_payment_report_submit"' in payment_model
    assert 'recordActionStarted("client_chat_message_send"' in chat_model
    assert 'recordActionStarted("client_order_dispute_open"' in chat_model
    assert 'recordActionStarted("support_ticket_create"' in support_model
    assert "setBusy(" not in marketplace_model
    assert "setBusy(" not in orders_model
    assert "setBusy(" not in payment_model
    assert "setBusy(" not in chat_model
    assert "disabled={busy" not in marketplace_screen
    assert "disabled={busy" not in order_screen
    assert "disabled={busy" not in payment_screen
    assert "disabled={busy" not in chat_screen
    assert "disabled={busy" not in support_screen
    assert "Buscando..." in marketplace_screen
    assert "Creando..." in order_screen
    assert "Cargando instrucciones..." in order_screen
    assert "Subiendo comprobante..." in payment_screen
    assert "Enviando reporte..." in payment_screen
    assert "Enviando..." in chat_screen
    assert "Abriendo..." in chat_screen
    assert "Creando..." in support_screen
    assert "openingChatOrderId: string | null" in remitter_types
    assert "recordBusinessActionStarted = recordActionStarted" in telemetry_helper
    assert "recordSlowSensitiveAction" in telemetry_helper


def test_business_ads_screen_has_readable_detail_and_edit_flow() -> None:
    ads_screen = _read("apps/web/src/screens/business-app/BusinessAdsScreens.tsx")
    ad_card = _read("apps/web/src/screens/business-app/ads/BusinessAdCard.tsx")
    ad_detail = _read("apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx")
    ad_helpers = _read("apps/web/src/screens/business-app/ads/businessAdViewHelpers.ts")
    ad_view_sources = "\n".join((ads_screen, ad_card, ad_detail, ad_helpers))
    ads_model = _read("apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts")
    ad_actions_model = _read("apps/web/src/hooks/business-mini-app/useBusinessAdActionsModel.ts")
    ads_api = _read("apps/web/src/api/businessAds.ts")
    business_api = _read("apps/web/src/api/businesses.ts")
    payment_methods_model = _read("apps/web/src/hooks/business-mini-app/useBusinessPaymentMethodsModel.ts")
    payment_method_helpers = _read("apps/web/src/hooks/business-mini-app/businessPaymentMethodHelpers.ts")
    business_shell = _read("apps/web/src/screens/business-app/BusinessMiniAppShell.tsx")
    globals_css = _read("apps/web/src/app/globals.css")
    pin_screen = _read("apps/web/src/screens/business-app/BusinessPinScreen.tsx")

    assert "BusinessAdDetailPanel" in ads_screen
    assert "BusinessAdCard" in ads_screen
    assert "function BusinessAdDetailPanel" in ad_detail
    assert "function BusinessAdCard" in ad_card
    assert "business-ad-card" in ad_card
    assert "business-list--scrollable" in ads_screen
    assert ">Ver<" in ad_card
    assert "Borrando..." in ad_view_sources
    assert "Republicando..." in ad_view_sources
    assert "Anuncio abierto" in ad_detail
    assert "Consume el credito de esta publicacion" in ad_view_sources
    assert "Tasa" in ad_view_sources
    assert "USDT TRC20" in ads_screen
    assert "Zelle - Bs" in ads_screen
    assert "USDT - Bs" in ads_screen
    assert "Wallet USDT TRC20 donde recibes" in ads_screen
    assert "Zelle donde recibes" in ads_screen
    assert "routeMethods.map" in ads_screen
    assert "selectAdPaymentType" in ads_screen
    assert "selectAdPaymentType" in payment_methods_model
    assert "Agrega una wallet USDT TRC20 para publicar USDT -> Bs." in ads_screen
    assert "Recibiras {previewAmount} USD y entregaras aprox. Bs." in ads_screen
    assert "Zelle y wallets USDT" in ads_screen
    assert "Si dejas Zelle o wallet vacio" in ads_screen
    assert "Metodos de cobro" not in ads_screen
    assert "Estas editando este metodo" not in ads_screen
    assert "Zelle / USDT" in ads_screen
    assert "mini-action-button--danger" in ads_screen
    assert "Borrando..." in ads_screen
    assert "startPaymentMethodCreate" in payment_methods_model
    assert "startPaymentMethodCreate" in ads_screen
    assert "activeBusinessPaymentMethods" in payment_methods_model
    assert 'return current.payment_method_id ? { ...current, payment_method_id: "" } : current;' in payment_methods_model
    assert "Confirmar borrar" in ads_screen
    assert "setConfirmDeleteId(method.id)" in ads_screen
    assert "void deletePaymentMethod(method.id)" in ads_screen
    assert "zelle-count-pill" in ads_screen
    assert 'cache: "no-store"' in business_api
    assert "/api/v1/business/payment-methods?_=${Date.now()}" in business_api
    assert 'type="button"' in ads_screen
    assert "paymentMethodCanReceive" in ad_helpers
    assert "Este anuncio usa un metodo borrado." in ad_detail
    assert "(borrado)" in ad_helpers
    assert "Edita el anuncio y selecciona un metodo activo para poder reactivarlo." in ad_detail
    assert "Agregar metodo" in ad_detail
    assert "Ese anuncio usa un metodo de cobro que ya no esta activo. Editalo y selecciona un metodo activo." in ad_actions_model
    assert '<div className="business-ad-card__main">' in ad_card
    assert 'onClick={onOpen}>Ver' in ad_card
    assert "disabled={busy} onClick={onOpen}>Ver" not in ad_card
    assert ".mini-action-button" in globals_css
    assert "-webkit-tap-highlight-color: transparent" in globals_css
    assert "PIN para borrar metodo" in pin_screen
    assert "Activar PIN y borrar metodo" in pin_screen
    assert "Borrar metodo" in pin_screen
    assert 'if (view === "my-ads")' in business_shell
    assert "deleteAd" in ads_model
    assert "republishAd" in ads_model
    assert "replaceOwnAd(data.ad)" in ad_actions_model
    assert "Reactivando anuncio..." in ad_actions_model
    assert "pausingAdId" in ad_actions_model
    assert "reactivatingAdId" in ad_actions_model
    assert "deletingAdId" in ad_actions_model
    assert "savingAdId" in ad_actions_model
    assert "loadingScreen" in ads_model
    assert '"ad_pause"' in ad_actions_model
    assert '"ad_reactivate"' in ad_actions_model
    assert '"ad_delete"' in ad_actions_model
    assert '"ad_republish"' in ad_actions_model
    assert "recordActionBreadcrumb(telemetryAction" in ad_actions_model
    assert 'recordActionBreadcrumb("ad_edit"' in ad_actions_model
    assert 'recordActionBreadcrumb("ad_create"' in ad_actions_model
    assert "disabled={isReactivating || !canReactivate}" in ad_view_sources
    assert 'disabled={isPausing || status !== "active"}' in ad_view_sources
    assert "disabled={isDeleting || !canDeleteAd(ad)}" in ad_view_sources
    assert 'disabled={busy || !canReactivate}' not in ad_view_sources
    assert 'disabled={busy || status !== "active"}' not in ad_view_sources
    assert "generatingCreditPayment" in _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    assert "verifyingCreditTx" in _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    assert "refreshingCreditPurchase" in _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    assert "savingPaymentMethodId" in ads_screen
    assert "deletingPaymentMethodId" in ads_screen
    assert "window.confirm" not in ads_screen
    assert "window.confirm" not in ad_detail
    assert "paymentMethodTelemetry" in payment_method_helpers
    assert "usdt_wallet_" in payment_method_helpers
    assert '"zelle_edit"' in payment_method_helpers
    assert '"zelle_add"' in payment_method_helpers
    assert "business_payment_method_create" in payment_methods_model
    assert "business_payment_method_update_" in payment_methods_model
    assert "business_payment_method_delete_" in payment_methods_model
    assert "`business_payment_method_${Date.now()}`" not in business_api
    assert "recordActionBreadcrumb(telemetryAction" in payment_methods_model
    assert "await refreshCreditWallet();" in ad_actions_model
    assert 'ad.status !== "paused"' not in ad_view_sources
    assert 'ad.status !== "active"' not in ad_view_sources
    assert "refreshCreditWallet" in ads_model
    assert "updateSelectedAd" in ads_model
    assert "updateBusinessAd" in ads_api
    assert '"republish"' in ads_api
    assert 'method: "PUT"' in ads_api
    assert ".business-list--scrollable" in globals_css


def test_business_action_breadcrumbs_do_not_include_sensitive_values() -> None:
    sensitive_fragments = (
        "authorization",
        "token",
        "wallet",
        "zelle_account",
        "baseusdctxhash",
        "tx_hash",
        "pinform",
        "pin:",
        "storage_path",
        "account_value",
        "private_key",
        "seed",
        "mnemonic",
    )
    for path in (
        "apps/web/src/hooks/actionTelemetry.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts",
    ):
        source = _read(path)
        for line in source.splitlines():
            if "recordActionBreadcrumb(" not in line and "recordBusinessAction" not in line:
                continue
            lowered = line.lower()
            assert all(fragment not in lowered for fragment in sensitive_fragments), f"{path} leaks sensitive breadcrumb input: {line}"
