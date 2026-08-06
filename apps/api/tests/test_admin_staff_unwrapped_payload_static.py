from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_staff_model_uses_unwrapped_api_payloads() -> None:
    source = _read("apps/web/src/hooks/admin-web/useAdminStaffModel.ts")

    assert 'from "../../types/admin"' in source
    assert "AdminStaffSummary" in source
    assert "AdminStaffDetail" in source
    assert "AdminStaffActivityItem" in source
    assert "AdminStaffPermissionInput" in source
    assert "listAdminStaff(request" in source
    assert "setStaff(response.items)" in source
    assert "getAdminStaff(request" in source
    assert "setSelectedStaff(response.staff)" in source
    assert "listAdminStaffActivity(request" in source
    assert "setStaffActivity(activity.items)" in source
    assert "export type StaffSummary" not in source
    assert "export type StaffDetail" not in source
    assert "export type StaffActivityItem" not in source
    assert "response.data.items" not in source
    assert "response.data.staff" not in source
    assert "activity.data.items" not in source


def test_admin_support_assignee_loader_uses_same_unwrapped_staff_contract() -> None:
    source = _read("apps/web/src/hooks/admin-web/useAdminSupportModel.ts")

    assert 'AdminStaffSummary' in source
    assert "listAdminStaff(request" in source
    assert "response.items.filter" in source
    assert "Boolean(response.next_cursor)" in source
    assert "response.data.items" not in source
    assert "response.data.next_cursor" not in source


def test_admin_staff_api_owns_concrete_unwrapped_response_types() -> None:
    api = _read("apps/web/src/api/admin.ts")
    types = _read("apps/web/src/types/admin.ts")
    client = _read("apps/web/src/api/client.ts")

    for type_name in (
        "AdminStaffPermissionInput",
        "AdminStaffSummary",
        "AdminStaffDetail",
        "AdminStaffActivityItem",
        "AdminStaffListResponse",
        "AdminStaffDetailResponse",
        "AdminStaffActivityResponse",
    ):
        assert f"export type {type_name}" in types

    for type_name in (
        "AdminStaffListResponse",
        "AdminStaffDetailResponse",
        "AdminStaffActivityResponse",
    ):
        assert type_name in api

    assert "return payload.data" in client
    assert "listAdminStaff<T>" not in api
    assert "getAdminStaff<T>" not in api
    assert "listAdminStaffActivity<T>" not in api
    assert "request<AdminStaffListResponse>" in api
    assert "request<AdminStaffDetailResponse>" in api
    assert "request<AdminStaffActivityResponse>" in api
