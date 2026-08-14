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
    assert "admin-web-orders-list-actions" in screen
    assert "public_order_code" in api
    assert "orderCodeFilter" in model
    assert "setOrderCodeFilter" in model
    assert ".admin-web-orders-list-scroll" in css
    assert "overflow-y: auto" in css
    assert ".admin-web-orders-panel" in css


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
    assert "business_id" in api
    assert "business_name" in api
    assert "businessSearchFilter" in business_model
    assert "businessSearchFilter" in web_model

    assert "admin-web-users-list-scroll" in users
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
    assert "Razon obligatoria para revelar telefono" in users
    assert "Indica el motivo operativo antes de revelar el telefono" in users
    assert "revealUserPhone" in web_model
    assert ".admin-web-businesses-list-scroll" in css
    assert ".admin-web-users-list-scroll" in css
