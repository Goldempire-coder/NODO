from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_operational_lists_consume_cursors_without_stale_replacement() -> None:
    cases = (
        ("useAdminBusinessesModel.ts", "businessesNextCursor", "businessesLoadingMore", "loadMoreBusinesses"),
        ("useAdminUsersModel.ts", "usersNextCursor", "usersLoadingMore", "loadMoreUsers"),
        (
            "useAdminCreditPurchasesModel.ts",
            "creditPurchasesNextCursor",
            "creditPurchasesLoadingMore",
            "loadMoreCreditPurchases",
        ),
        (
            "useAdminCreditTransactionsModel.ts",
            "creditTransactionsNextCursor",
            "creditTransactionsLoadingMore",
            "loadMoreCreditTransactions",
        ),
        ("useAdminAuditLogsModel.ts", "auditLogsNextCursor", "auditLogsLoadingMore", "loadMoreAuditLogs"),
        ("useAdminJobsModel.ts", "jobRunsNextCursor", "jobRunsLoadingMore", "loadMoreJobs"),
        (
            "useAdminNotificationsModel.ts",
            "notificationsNextCursor",
            "notificationsLoadingMore",
            "loadMoreNotifications",
        ),
    )

    for filename, cursor_state, loading_state, load_more in cases:
        source = _read(f"apps/web/src/hooks/admin-web/{filename}")
        assert cursor_state in source
        assert loading_state in source
        assert load_more in source
        if filename == "useAdminCreditTransactionsModel.ts":
            assert "appendUniqueTransactions" in source
            assert "purchase_id" in source
        else:
            assert "appendUniqueById" in source
        assert "RequestEpoch" in source or "requestEpoch" in source


def test_admin_operational_screens_offer_guarded_load_more_actions() -> None:
    cases = (
        ("AdminBusinessScreens.tsx", "businessesNextCursor", "businessesLoadingMore", "loadMoreBusinesses"),
        ("AdminUserScreens.tsx", "usersNextCursor", "usersLoadingMore", "loadMoreUsers"),
        (
            "AdminCreditScreens.tsx",
            "creditPurchasesNextCursor",
            "creditPurchasesLoadingMore",
            "loadMoreCreditPurchases",
        ),
        (
            "AdminCreditScreens.tsx",
            "creditTransactionsNextCursor",
            "creditTransactionsLoadingMore",
            "loadMoreCreditTransactions",
        ),
        ("AdminAuditScreens.tsx", "auditLogsNextCursor", "auditLogsLoadingMore", "loadMoreAuditLogs"),
        ("AdminOverviewScreens.tsx", "jobRunsNextCursor", "jobRunsLoadingMore", "loadMoreJobs"),
        (
            "AdminWebShell.tsx",
            "adminNotificationsNextCursor",
            "adminNotificationsLoadingMore",
            "loadMoreAdminNotifications",
        ),
    )

    for filename, cursor_state, loading_state, load_more in cases:
        source = _read(f"apps/web/src/screens/admin-web/{filename}")
        assert cursor_state in source
        assert loading_state in source
        assert load_more in source
        assert "Cargar mas" in source


def test_intake_load_more_blocks_overlap_and_discards_stale_results() -> None:
    model = _read("apps/web/src/hooks/admin-web/useAdminBusinessIntakesModel.ts")
    screen = _read("apps/web/src/screens/admin-web/AdminBusinessIntakeScreens.tsx")

    assert "businessIntakesLoadingMore" in model
    assert "requestEpoch" in model
    assert "if (!businessIntakesNextCursor || businessIntakesLoadingMore)" in model
    assert "businessIntakesLoadingMore" in screen
    assert "disabled={model.businessIntakesLoadingMore}" in screen


def test_touched_admin_list_apis_use_concrete_dtos_and_forward_cursor() -> None:
    api = _read("apps/web/src/api/admin.ts")
    types = _read("apps/web/src/types/admin.ts")

    for function_name in (
        "listAdminBusinesses",
        "listAdminUsers",
        "listAdminAuditLogs",
        "listAdminCreditPurchases",
        "listAdminCreditTransactions",
        "listAdminJobRuns",
        "listAdminBusinessIntakes",
        "listAdminNotifications",
    ):
        assert f"{function_name}<T>" not in api
    for dto in (
        "AdminBusinessListResponse",
        "AdminUserListResponse",
        "AdminAuditLogListResponse",
        "AdminCreditPurchaseListResponse",
        "AdminCreditTransactionListResponse",
        "AdminJobRunListResponse",
        "AdminBusinessIntakeListResponse",
        "AdminNotificationsList",
    ):
        assert f"export type {dto}" in types
    assert api.count('params.set("cursor", cursor)') >= 8
    assert "listPendingAdminBusinesses" not in api
    assert "businesses/pending" not in api


def test_admin_order_timeline_is_not_silently_truncated() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminOrderDisputeScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert ".slice(0, 6)" not in screen
    assert "admin-web-order-timeline-scroll" in screen
    assert ".admin-web-order-timeline-scroll" in css
    assert "overflow-y: auto" in css
