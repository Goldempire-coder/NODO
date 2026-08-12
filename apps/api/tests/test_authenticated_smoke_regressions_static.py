from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_business_authorization_is_not_revoked_by_secondary_load_failures() -> None:
    source = _read("apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts")

    ready = source.index('setAccessState("ready")')
    secondary_loads = source.index("Promise.allSettled")
    assert ready < secondary_loads
    assert "Acceso validado. No pudimos cargar todos los datos; usa Actualizar." in source
    assert "await Promise.all([" not in source


def test_client_profile_updates_the_persisted_telegram_session() -> None:
    session = _read("apps/web/src/api/session.ts")
    workspace = _read("apps/web/src/hooks/useClientWorkspaceModel.ts")

    assert "export function updateAuthSessionUser" in session
    assert 'updateAuthSessionUser("telegram", updatedUser)' in workspace
    assert workspace.count('updateAuthSessionUser("telegram", updatedUser)') == 2


def test_admin_dashboard_recovery_only_clears_its_matching_stale_error() -> None:
    root_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    overview = _read("apps/web/src/hooks/admin-web/useAdminOverviewModel.ts")
    dashboard = _read("apps/web/src/hooks/admin-web/useAdminDashboardMetricsModel.ts")

    assert "clearNoticeIf" in root_model
    assert "clearNoticeIf" in overview
    assert "dashboardErrorRef" in dashboard
    assert "clearNoticeIf(staleError)" in dashboard


def test_admin_mobile_notification_panel_stays_inside_the_viewport() -> None:
    css = _read("apps/web/src/app/admin-web.css")
    mobile = css[css.index("@media (max-width: 600px)") :]

    assert ".admin-web-notifications" in mobile
    assert "width: 100%;" in mobile
    assert ".admin-web-notification-panel" in mobile
    assert "left: 0;" in mobile
    assert "right: auto;" in mobile
    assert "max-height: min(480px, calc(100dvh - 340px));" in mobile
