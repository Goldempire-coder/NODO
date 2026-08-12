from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_surface_support_polling_is_visible_only_non_overlapping_and_cleans_up() -> None:
    polling = _read("apps/web/src/hooks/useVisibleSurfacePolling.ts")
    client = _read("apps/web/src/screens/client/ClientSupportScreen.tsx")
    business = _read("apps/web/src/screens/business-app/BusinessSupportScreen.tsx")

    assert 'document.visibilityState !== "visible"' in polling
    assert "inFlightRef.current" in polling
    assert 'document.addEventListener("visibilitychange"' in polling
    assert 'document.removeEventListener("visibilitychange"' in polling
    assert "window.clearInterval(interval)" in polling
    assert "generationRef.current += 1" in polling
    for screen in (client, business):
        assert "useVisibleSurfacePolling" in screen
        assert "window.setInterval" not in screen
        assert 'notice.startsWith("No ")' not in screen


def test_surface_support_refresh_discards_late_results_without_touching_composer() -> None:
    model = _read("apps/web/src/hooks/useSurfaceSupportModel.ts")

    assert "supportRefreshEpochRef" in model
    assert "supportRefreshInFlightRef" in model
    assert "return runSupportRefresh();" in model
    assert "supportRefreshEpochRef.current += 1" in model
    assert "shouldApply" in model
    assert "isLatest" in model
    assert "selectedSupportTicketRef.current?.id" in model
    refresh = model.split("const refreshSupportWorkspace", 1)[1].split("const openSupportTicket", 1)[0]
    assert "setSupportReply" not in refresh
