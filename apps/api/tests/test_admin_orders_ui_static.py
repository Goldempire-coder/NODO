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
    assert "DIAGNOSTIC_REFRESH_REQUIRED" in business_model
    assert "No pudimos refrescar el diagnostico; usa Actualizar." in business_model
    pending_index = business_model.index("DIAGNOSTIC_REFRESH_REQUIRED")
    refresh_index = business_model.index("await loadBusinessDetail(businessId)", pending_index)
    assert pending_index < refresh_index
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
