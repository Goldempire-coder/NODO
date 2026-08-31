from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_orders_screen_has_code_filter_and_internal_scroll() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")
    model = _read("apps/web/src/hooks/admin-web/useAdminOrdersModel.ts")
    api = _read("apps/web/src/api/admin.ts")
    css = _read("apps/web/src/app/admin-web.css")

    assert "orderCodeFilter" in screen
    assert "setOrderCodeFilter" in screen
    assert 'placeholder="NODO-7C25CBC6"' in screen
    assert "admin-web-orders-list-scroll" in screen
    assert 'aria-label="Lista de ordenes admin"' in screen
    assert "admin-web-orders-list-actions" in screen
    assert "public_order_code" in api
    assert "orderCodeFilter" in model
    assert "setOrderCodeFilter" in model
    assert ".admin-web-orders-list-scroll" in css
    assert "overflow-y: auto" in css
    assert ".admin-web-orders-panel" in css


def test_admin_order_detail_keeps_chat_visible_with_bounded_panels() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert "admin-order-detail-layout" in screen
    assert "admin-order-detail-facts" in screen
    assert "admin-order-report-facts" in screen
    assert "AdminOrderChatEvidencePanel" in screen
    assert ".admin-order-detail-layout .admin-web-panel" in css
    assert ".admin-order-detail-summary .admin-order-detail-facts" in css
    assert ".admin-order-detail-summary .admin-order-report-facts" in css
    assert ".admin-web-order-timeline-scroll" in css
    assert "max-height: min(236px, 32dvh)" in css
    assert ".admin-web-order-timeline-scroll .admin-web-row" in css
    assert ".admin-order-chat-evidence__messages" in css
    assert ".admin-order-chat-evidence {\n  display: flex;" in css
    assert ".admin-order-chat-evidence.is-collapsed" in css
    assert "height: auto;" in css
    assert ".admin-order-chat-evidence__lazy" in css
    assert "flex-direction: column;" in css
    assert "height: clamp(300px, 40dvh, 460px)" in css
    assert "flex: 1 1 auto" in css
    assert "overflow-y: scroll" in css
    assert "-webkit-overflow-scrolling: touch" in css
    assert "scrollbar-gutter: stable" in css


def test_support_admin_navigation_stays_limited_to_support_queue() -> None:
    access = _read("apps/web/src/hooks/admin-web/adminWebAccess.ts")
    web_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    policy = _read("apps/api/app/modules/admin/policy.py")
    admin_service = _read("apps/api/app/modules/admin/service.py")
    chat_evidence_service = _read("apps/api/app/modules/admin/order_chat_evidence.py")

    assert "canReadAdminOperations" in access
    assert 'user.role === "admin" || user.role === "super_admin"' in access
    assert "const supportNavigation" in web_model
    assert "if (!adminOperationsReadable)" in web_model
    assert 'view: "support" as const' in web_model
    assert "void support.loadSupportTickets(\"active\")" in web_model
    assert "require_admin_operations_read" in policy
    assert "require_admin_operations_read(user)" in admin_service
    assert "require_admin_operations_read(user)" in chat_evidence_service


def test_admin_disputes_screen_has_internal_scroll() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert "admin-web-disputes-panel" in screen
    assert "admin-web-disputes-list-scroll" in screen
    assert 'aria-label="Lista de disputas admin"' in screen
    assert ".admin-web-disputes-panel" in css
    assert ".admin-web-disputes-list-scroll" in css
    assert ".admin-web-disputes-list-scroll:focus-visible" in css
    assert ".admin-web-disputes-list-scroll .admin-web-table th" in css


def test_admin_credit_purchases_screen_has_internal_scroll() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminCreditScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert "admin-web-credit-purchases-panel" in screen
    assert "admin-web-credit-purchases-list-scroll" in screen
    assert 'aria-label="Lista de compras de creditos admin"' in screen
    assert ".admin-web-credit-purchases-panel" in css
    assert ".admin-web-credit-purchases-list-scroll" in css
    assert ".admin-web-credit-purchases-list-scroll:focus-visible" in css
    assert ".admin-web-credit-purchases-list-scroll .admin-web-table th" in css


def test_admin_audit_logs_screen_has_internal_scroll() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminAuditScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert "admin-web-audit-logs-panel" in screen
    assert "admin-web-audit-logs-list-scroll" in screen
    assert 'aria-label="Lista de audit logs admin"' in screen
    assert ".admin-web-audit-logs-panel" in css
    assert ".admin-web-audit-logs-list-scroll" in css
    assert ".admin-web-audit-logs-list-scroll:focus-visible" in css
    assert ".admin-web-audit-logs-list-scroll .admin-web-table th" in css


def test_admin_business_intake_screen_has_internal_scroll() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminBusinessIntakeScreens.tsx")
    model = _read("apps/web/src/hooks/admin-web/useAdminBusinessIntakesModel.ts")
    api = _read("apps/web/src/api/admin.ts")
    css = _read("apps/web/src/app/admin-web.css")

    assert "admin-web-business-intake-panel" in screen
    assert "admin-web-business-intake-list-scroll" in screen
    assert 'aria-label="Lista de intake de negocios admin"' in screen
    assert "intakeReadinessFilter" in screen
    assert "setIntakeReadinessFilter" in screen
    assert "businessIntakesNextCursor" in screen
    assert "loadMoreBusinessIntakes" in screen
    assert "Cargar mas" in screen
    assert "Listas primero" in screen
    assert "Solo listas" in screen
    assert "Faltan datos" in screen
    assert "ready_for_review" in screen
    assert "review_missing_count" in screen
    assert "intakeReadinessFilter" in model
    assert "setIntakeReadinessFilter" in model
    assert "businessIntakesNextCursor" in model
    assert "loadMoreBusinessIntakes" in model
    assert "readiness" in api
    assert "cursor" in api
    assert ".admin-web-business-intake-panel" in css
    assert ".admin-web-business-intake-list-scroll" in css
    assert ".admin-web-intake-ready" in css
    assert ".admin-web-intake-missing" in css
    assert ".admin-web-business-intake-list-scroll:focus-visible" in css
    assert ".admin-web-business-intake-list-scroll .admin-web-table th" in css


def test_admin_businesses_and_users_have_targeted_filters_and_internal_scroll() -> None:
    businesses = _read("apps/web/src/screens/admin-web/AdminBusinessScreens.tsx")
    users = _read("apps/web/src/screens/admin-web/AdminUserScreens.tsx")
    web_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    business_model = _read("apps/web/src/hooks/admin-web/useAdminBusinessesModel.ts")
    user_model = _read("apps/web/src/hooks/admin-web/useAdminUsersModel.ts")
    api = _read("apps/web/src/api/admin.ts")
    css = _read("apps/web/src/app/admin-web.css")

    assert "businessSearchFilter" in businesses
    assert "setBusinessSearchFilter" in businesses
    assert 'placeholder="ID o nombre del negocio"' in businesses
    assert "admin-web-businesses-list-scroll" in businesses
    assert 'aria-label="Lista de negocios admin"' in businesses
    assert "business_id" in api
    assert "business_name" in api
    assert "businessSearchFilter" in business_model
    assert "businessSearchFilter" in web_model
    assert "Activar acceso" in businesses
    assert 'detail.business.verification_status !== "approved"' in businesses
    assert "canEnterBusinessApp" in businesses
    assert "detail.access_diagnostic" in businesses
    assert "Puede entrar" in businesses
    assert "No puede entrar" in businesses
    assert "La cuenta del dueno esta bloqueada" in businesses
    assert "Desbloquear dueno" in businesses
    assert "El negocio esta bloqueado" in businesses
    assert "El negocio esta suspendido" in businesses
    assert "Estado operativo del negocio" in businesses
    assert "Desbloquear negocio" in businesses
    assert "Razon obligatoria para cambiar estado del negocio" in businesses
    assert "Indica el motivo operativo antes de cambiar el estado" in businesses
    assert "changeBusinessStatus" in businesses
    assert "changeBusinessOwnerUserStatus" in businesses
    assert "{ requiresReason: true }" in business_model
    assert "updateAdminUserStatus" in business_model
    assert "updateAdminBusinessStatus" in api
    assert "Negocio aprobado, pero el dueno aun no puede entrar" in businesses
    assert "Sin accesos activos para este negocio" in businesses
    assert ".admin-web-inline-warning" in css
    assert ".admin-web-business-access-summary" in css
    assert ".admin-web-business-access-gates" in css
    assert "finishAccessMutation" in business_model
    assert "businessAccessActionFeedback" in business_model
    assert "businessAccessDiagnosticPending" in business_model
    assert "Actualiza para confirmar." in business_model
    assert "access_diagnostic: data.access_diagnostic" in business_model
    assert "affected_access_links" in business_model
    assert "mergeAffectedAccessLinks(current, data.affected_access_links, data.access_link)" in business_model
    assert "DIAGNOSTIC_REFRESH_REQUIRED" not in business_model
    assert 'target: `link:${linkId}`' in business_model
    assert '{ requiresReason: true }' in business_model
    assert "admin-web-access-action-feedback" in businesses
    assert "Actualizar" in businesses
    assert "Razon obligatoria para cambiar el acceso" in businesses
    assert "Indica el motivo operativo antes de cambiar el acceso" in businesses
    assert "No pudimos confirmar el diagnostico actualizado. Usa Actualizar." in businesses
    assert "Failed to fetch" not in business_model
    response_index = business_model.index("const data = await updateAdminBusinessAccessLink")
    local_update_index = business_model.index("mergeAffectedAccessLinks(current, data.affected_access_links, data.access_link)", response_index)
    refresh_index = business_model.index("await finishAccessMutation", local_update_index)
    assert response_index < local_update_index < refresh_index
    manual_refresh_index = business_model.index("const errorMessage = await loadBusinessDetail(businessId)")
    clear_pending_index = business_model.index("setBusinessAccessDiagnosticPending(false)", manual_refresh_index)
    assert business_model.index("if (!errorMessage)", manual_refresh_index) < clear_pending_index
    assert "admin-web-users-list-scroll" in users
    assert 'aria-label="Lista de clientes admin"' in users
    assert "revealUserPhone" in users
    assert "Ver telefono" in users
    assert "phone/reveal" in api
    assert "revealedUserPhones" not in user_model
    assert "revealedUserPhone" in user_model
    assert "activeUserDetailRef" in user_model
    assert "activeUserDetailRef.current !== userId" in user_model
    assert user_model.index("activeUserDetailRef.current !== userId") < user_model.index("setRevealedUserPhone(data)")
    assert 'view !== "user-detail"' in user_model
    assert user_model.count("setRevealedUserPhone(null)") >= 3
    assert "user: { ...current.user, phone: data.phone" not in user_model
    assert "mientras mantengas abierto este detalle" in user_model
    assert "Razon obligatoria para acciones sensibles" in users
    assert "Indica el motivo operativo antes de revelar telefono o cambiar estado" in users
    assert "revealUserPhone" in web_model
    assert ".admin-web-businesses-list-scroll" in css
    assert ".admin-web-businesses-list-scroll {\n  height:" in css
    assert "overflow-y: scroll" in css
    assert ".admin-web-users-list-scroll" in css
    assert ".admin-web-businesses-list-scroll:focus-visible" in css


def test_admin_business_access_panel_uses_backend_diagnostic_as_authority() -> None:
    businesses = _read("apps/web/src/screens/admin-web/AdminBusinessScreens.tsx")

    assert "detail.access_diagnostic" in businesses
    assert "diagnostic.business_can_access_surface" in businesses
    assert "diagnostic.blocking_reason" in businesses
    assert "diagnostic.recommended_admin_action" in businesses
    assert "diagnostic.owner_link_role" in businesses
    assert "BUSINESS_ACCESS_LINK_REQUIRED" in businesses
    assert "Crear vinculo owner." in businesses
    assert 'businessStatus === "approved" && activeAccessCount > 0' not in businesses


def test_admin_business_capacity_copy_and_refresh_failure_are_clear() -> None:
    businesses = _read("apps/web/src/screens/admin-web/AdminBusinessScreens.tsx")
    business_model = _read("apps/web/src/hooks/admin-web/useAdminBusinessesModel.ts")

    assert "Maximo por operacion (USD)" in businesses
    assert "Capacidad maxima diaria (USD)" in businesses
    assert "Disponible operativo ahora (USD)" in businesses
    assert "Primero guarda la capacidad maxima diaria" in businesses
    assert "const data = await updateAdminBusinessCapacity" in business_model
    assert "Capacidad del negocio actualizada. No pudimos refrescar el detalle; usa Actualizar." in business_model
    assert "business: { ...current.business, ...data.business }" in business_model
    capacity_response_index = business_model.index("const data = await updateAdminBusinessCapacity")
    local_update_index = business_model.index("business: { ...current.business, ...data.business }", capacity_response_index)
    refresh_index = business_model.index("await loadBusinessDetail(selectedBusiness.business.id)", local_update_index)
    assert capacity_response_index < local_update_index < refresh_index


def test_admin_and_business_referral_surfaces_match_intake_approval_rule() -> None:
    admin_businesses = _read("apps/web/src/screens/admin-web/AdminBusinessScreens.tsx")
    business_credits = _read("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx")
    business_credits_model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    credits_api = _read("apps/web/src/api/credits.ts")

    assert "detail.referrals.referred_by" in admin_businesses
    assert "detail.referrals.referred_businesses" in admin_businesses
    assert "detail.referrals.earned_credits" in admin_businesses
    assert "detail.referrals.remaining_bonus_credits" in admin_businesses
    assert "Aplicar codigo" not in business_credits
    assert "referralData.referral_code" in business_credits
    assert "referralData.earned_credits" in business_credits
    assert "referralData.remaining_bonus_credits" in business_credits
    for legacy_reference in (
        "applyBusinessReferral",
        "applyReferral",
        "referralCodeInput",
        "setReferralCodeInput",
        "primera compra aprobada",
        "/business/referrals/apply",
    ):
        assert legacy_reference not in business_credits_model
        assert legacy_reference not in credits_api
