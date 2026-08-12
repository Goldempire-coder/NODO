from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_polling_is_visible_only_non_overlapping_and_cleans_up() -> None:
    admin_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    polling = _read("apps/web/src/hooks/admin-web/useVisibleAdminPolling.ts")

    assert admin_model.count("useVisibleAdminPolling({") == 2
    assert 'view === "support"' in admin_model
    assert "document.visibilityState !== \"visible\"" in polling
    assert "inFlightRef.current" in polling
    assert 'document.addEventListener("visibilitychange"' in polling
    assert 'document.removeEventListener("visibilitychange"' in polling
    assert "window.clearInterval(interval)" in polling
    assert "generationRef.current += 1" in polling
    assert "isCurrent" in polling


def test_admin_background_models_discard_late_refresh_responses() -> None:
    dashboard = _read("apps/web/src/hooks/admin-web/useAdminDashboardMetricsModel.ts")
    notifications = _read("apps/web/src/hooks/admin-web/useAdminNotificationsModel.ts")
    support = _read("apps/web/src/hooks/admin-web/useAdminSupportModel.ts")

    for source in (dashboard, notifications, support):
        assert "requestEpoch" in source
        assert "shouldApply" in source
        assert "isLatest" in source

    assert "refreshSupportWorkspace" in support
    assert "selectedSupportTicket" in support
    assert "foregroundDashboardRequests.current > 0" in dashboard
    assert "foregroundSupportRequests.current > 0" in support


def test_admin_critical_confirmation_has_required_copy_dialog_semantics_and_focus() -> None:
    dashboard = _read("apps/web/src/screens/admin-web/AdminDashboardScreen.tsx")
    shell = _read("apps/web/src/screens/admin-web/AdminWebShell.tsx")

    assert 'label="Razon obligatoria"' in dashboard
    assert 'placeholder="Escribe el motivo operativo para auditar esta accion."' in dashboard
    assert 'label="Reason obligatorio"' not in dashboard
    assert 'role="dialog"' in shell
    assert 'aria-labelledby="admin-web-confirm-title"' in shell
    assert 'aria-describedby="admin-web-confirm-detail"' in shell
    assert "confirmCancelRef.current?.focus()" in shell
    assert "previousFocusRef.current?.focus()" in shell
