from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_publication_hold_contract_is_owned_by_admin_types_and_api() -> None:
    types = _read("apps/web/src/types/admin.ts")
    support_api = _read("apps/web/src/api/support.ts")

    assert "export type AdminBusinessPublicationHold" in types
    assert "export type AdminSupportTicket" in types
    assert "export type AdminPublicationHoldReleaseResponse" in types
    assert "releaseAdminBusinessPublicationHold" in support_api
    assert "/api/v1/admin/business-publication-holds/${holdId}/release" in support_api
    assert '"Idempotency-Key": idempotencyKey' in support_api
    assert "body: JSON.stringify({ reason })" in support_api


def test_admin_publication_hold_model_requires_reason_and_stable_idempotency() -> None:
    model = _read("apps/web/src/hooks/admin-web/useAdminPublicationHoldModel.ts")

    assert "useStableIdempotencyKeys" in model
    assert "getIdempotencyKey" in model
    assert "clearIdempotencyKey" in model
    assert "releaseAdminBusinessPublicationHold" in model
    assert "publicationHoldReleaseInFlight" in model
    assert "PublicationHoldReleaseDraft" in model
    assert "releaseDraft.ticketId === selectedTicketId" in model
    assert "Escribe una razon para liberar la publicacion." in model
    assert "queueCriticalAction" in model
    assert 'requiresReason: false' in model
    assert "await refreshTicket(ticketId)" in model
    assert model.index("clearIdempotencyKey(idempotencyScope);") > model.index("await releaseAdminBusinessPublicationHold")


def test_release_success_is_applied_before_best_effort_ticket_refresh() -> None:
    model = _read("apps/web/src/hooks/admin-web/useAdminPublicationHoldModel.ts")
    support_model = _read("apps/web/src/hooks/admin-web/useAdminSupportModel.ts")

    release_position = model.index("releaseResult = await releaseAdminBusinessPublicationHold")
    clear_position = model.index("clearIdempotencyKey(idempotencyScope);")
    apply_position = model.index("applyReleasedHold(ticketId, releaseResult.hold);")
    refresh_position = model.index("await refreshTicket(ticketId);")

    assert release_position < clear_position < apply_position < refresh_position
    assert model.count("clearIdempotencyKey(idempotencyScope);") == 1
    assert "Hold liberado. No pudimos refrescar el ticket; usa Actualizar." in model
    assert "try {\n            await refreshTicket(ticketId);\n          } catch {" in model
    assert "applyReleasedHold" in support_model
    assert "publication_hold: hold" in support_model


def test_admin_support_renders_pure_hold_panel_and_refreshes_ticket() -> None:
    support_model = _read("apps/web/src/hooks/admin-web/useAdminSupportModel.ts")
    admin_model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    screen = _read("apps/web/src/screens/admin-web/AdminSupportScreens.tsx")
    panel = _read("apps/web/src/screens/admin-web/AdminPublicationHoldPanel.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert "useAdminPublicationHoldModel" in support_model
    assert "...publicationHold" in support_model
    assert "publicationHoldReleaseReason: support.publicationHoldReleaseReason" in admin_model
    assert "requestPublicationHoldRelease: support.requestPublicationHoldRelease" in admin_model
    assert "AdminPublicationHoldPanel" in screen
    assert "selected.publication_hold" in screen

    assert 'data-status={hold?.status || "none"}' in panel
    assert 'hold?.status === "active"' in panel
    assert "Liberar publicacion" in panel
    assert "El negocio podra volver a publicar si no tiene otro bloqueo activo." in panel
    assert "Razon obligatoria" in panel
    assert "No hay hold operativo asociado a este ticket." in panel
    assert "onRequestRelease" in panel
    assert "model.requestPublicationHoldRelease" in screen
    assert "admin-publication-hold__error" in panel

    for class_name in (
        ".admin-publication-hold",
        ".admin-publication-hold__header",
        ".admin-publication-hold__details",
        ".admin-publication-hold__action",
        ".admin-publication-hold__error",
    ):
        assert class_name in css


def test_publication_hold_panel_does_not_render_private_causal_data_or_leak_surfaces() -> None:
    panel = _read("apps/web/src/screens/admin-web/AdminPublicationHoldPanel.tsx").lower()
    client_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "apps/web/src/screens/client").rglob("*.tsx")
    )
    business_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "apps/web/src/screens/business-app").rglob("*.tsx")
    )

    for forbidden in (
        "rating",
        "estrellas",
        "cliente causante",
        "mensaje del ticket",
        "telefono",
        "banco",
        "wallet",
        "signed_url",
        "storage_path",
        "evidencia privada",
    ):
        assert forbidden not in panel

    assert "AdminPublicationHoldPanel" not in client_sources
    assert "AdminPublicationHoldPanel" not in business_sources
