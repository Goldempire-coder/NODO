from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_dashboard_preserves_operational_actions_without_mock_metrics() -> None:
    dashboard = _read("apps/web/src/screens/admin-web/AdminDashboardScreen.tsx")

    for action in (
        'model.loadBusinessIntakes("submitted")',
        "model.loadPendingBusinesses()",
        'model.loadCreditPurchases("pending_manual_review")',
        'model.loadDisputes("open")',
        "model.loadAuditLogs()",
    ):
        assert action in dashboard

    for forbidden in (
        "recent_client_contacts",
        "client_profiles_with_phone",
        "oldest_age_hours",
        "delta_24h",
        "generated_at",
        "severity",
        '"Hoy"',
        '"7d"',
        '"30d"',
    ):
        assert forbidden not in dashboard


def test_admin_dashboard_keeps_emergency_permissions_reason_and_confirmation_flow() -> None:
    dashboard = _read("apps/web/src/screens/admin-web/AdminDashboardScreen.tsx")

    assert "<ReasonBox" in dashboard
    assert "!model.adminMutable" in dashboard
    assert "model.activateEmergencyMode()" in dashboard
    assert "model.deactivateEmergencyMode()" in dashboard
    assert "model.loadEmergencyMode()" in dashboard
    assert "model.setEmergencyMessage" in dashboard


def test_admin_dashboard_uses_isolated_compact_layout_and_bounded_queue_scroll() -> None:
    dashboard = _read("apps/web/src/screens/admin-web/AdminDashboardScreen.tsx")
    screens = _read("apps/web/src/screens/admin-web/AdminWebScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert 'import { Dashboard } from "./AdminDashboardScreen";' in screens
    assert "admin-dashboard-kpi-grid" in dashboard
    assert "admin-dashboard-queue-list" in dashboard
    assert "admin-dashboard-quick-actions" in dashboard
    assert "admin-dashboard-emergency" in dashboard
    assert ".admin-dashboard-queue-list" in css
    assert "max-height: 320px" in css
    assert "overflow-y: auto" in css
    assert "grid-auto-rows: 64px" in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(64px, 64px) minmax(148px, 148px)" in css
    assert "font-variant-numeric: tabular-nums" in css
    assert "text-overflow: ellipsis" in css
    assert "height: 100dvh" in css


def test_admin_dashboard_has_non_numeric_loading_and_retry_state() -> None:
    dashboard = _read("apps/web/src/screens/admin-web/AdminDashboardScreen.tsx")

    assert "if (!data)" in dashboard
    assert 'aria-busy={model.busy}' in dashboard
    assert "model.loadDashboard()" in dashboard
    assert "admin-dashboard-skeleton" in dashboard
