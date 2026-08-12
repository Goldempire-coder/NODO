from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_orders_disputes_and_support_use_concrete_api_dtos() -> None:
    api = _read("apps/web/src/api/admin.ts")
    types = _read("apps/web/src/types/admin.ts")
    order_hook = _read("apps/web/src/hooks/admin-web/useAdminOrdersModel.ts")
    dispute_hook = _read("apps/web/src/hooks/admin-web/useAdminDisputesModel.ts")

    for generic_api in (
        "listAdminOrders<T>",
        "getAdminOrder<T>",
        "listAdminDisputes<T>",
        "getAdminDispute<T>",
        "resolveAdminDispute<T>",
    ):
        assert generic_api not in api
    for dto in (
        "AdminOrderListResponse",
        "AdminOrderDetailResponse",
        "AdminDisputeListResponse",
        "AdminDisputeDetailResponse",
        "AdminSupportTicketListResponse",
    ):
        assert f"export type {dto}" in types
    assert "ListResponse<" not in order_hook
    assert "ListResponse<" not in dispute_hook
    assert "response.data.items" not in order_hook + dispute_hook
