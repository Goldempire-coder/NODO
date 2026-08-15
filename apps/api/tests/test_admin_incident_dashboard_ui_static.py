from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_overview_tables_have_internal_scroll() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminOverviewScreens.tsx")
    primitives = _read("apps/web/src/screens/admin-web/AdminWebPrimitives.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert "ScrollableTable" in primitives
    assert "admin-web-table-scroll" in primitives
    assert screen.count("<ScrollableTable") >= 10
    for label in [
        "Checks de dependencias",
        "Jobs recientes con problemas",
        "Notificaciones con problemas",
        "Actividad reciente",
        "UX por superficie",
        "Pantallas con mas friccion",
        "Acciones con problemas",
        "Errores API visibles al usuario",
        "Friccion reciente",
        "Jobs admin",
    ]:
        assert f'label="{label}"' in screen

    assert ".admin-web-table-scroll" in css
    assert "max-height: min(360px, 42dvh)" in css
    assert "overflow-y: auto" in css
    assert ".admin-web-table-scroll .admin-web-table th" in css
    assert "position: sticky" in css
