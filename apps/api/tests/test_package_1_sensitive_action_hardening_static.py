from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _idempotency_lines(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if "Idempotency" in line or "idempotency" in line)


def test_base_usdc_credit_watcher_runtime_is_wired_without_sensitive_logs() -> None:
    main_source = _read("apps/api/app/main.py")
    config_source = _read("apps/api/app/core/config.py")
    env_example = _read(".env.example")
    watcher_loop = main_source.split("async def _base_usdc_credit_watcher_loop", 1)[1].split("def _configure_test_state", 1)[0]

    assert "onchain_credit_watcher_enabled" in config_source
    assert "ONCHAIN_CREDIT_WATCHER_ENABLED" in config_source
    assert "onchain_credit_watcher_interval_seconds" in config_source
    assert "task_group.start_soon(_base_usdc_credit_watcher_loop" in main_source
    assert "verify_base_usdc_credit_purchases_worker.run_once" in watcher_loop
    assert "scheduler_base_usdc_credit_watcher" in watcher_loop
    assert "base_usdc_credit_watcher_finished" in watcher_loop
    assert "base_usdc_credit_watcher_failed" in watcher_loop
    assert "errors_count" in watcher_loop
    assert "ONCHAIN_CREDIT_WATCHER_ENABLED=0" in env_example
    assert "ONCHAIN_CREDIT_WATCHER_INTERVAL_SECONDS=30" in env_example
    assert "TELEGRAM_WEB_APP_URL=http://localhost:3000" in env_example
    assert "ORDER_NOTIFICATION_SENDER_ENABLED=1" in env_example
    assert "ORDER_NOTIFICATION_SENDER_INTERVAL_SECONDS=10" in env_example

    for sensitive_fragment in ("tx_hash", "destination_wallet", "base_rpc_url", "rpc_url", "wallet_address"):
        assert sensitive_fragment not in watcher_loop.lower()


def test_sensitive_actions_use_stable_idempotency_keys_without_timestamp_headers() -> None:
    stable_helper = _read("apps/web/src/hooks/useStableIdempotencyKeys.ts")
    support_api = _read("apps/web/src/api/support.ts")

    assert "stableJson" in stable_helper
    assert "useStableIdempotencyKeys" in stable_helper
    assert "getIdempotencyKey" in stable_helper
    assert "clearIdempotencyKey" in stable_helper
    assert "Date.now()" not in _idempotency_lines(stable_helper)
    assert "Date.now()" not in _idempotency_lines(support_api)

    hook_paths = (
        "apps/web/src/hooks/business-mini-app/useBusinessAdActionsModel.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessAvailabilityModel.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatAttachments.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatComposer.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessPaymentShareActions.ts",
        "apps/web/src/hooks/business-mini-app/chat/useBusinessChatOrderActions.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts",
        "apps/web/src/hooks/business-mini-app/useBusinessPaymentMethodsModel.ts",
        "apps/web/src/hooks/useSurfaceSupportModel.ts",
        "apps/web/src/hooks/admin-web/useAdminSupportModel.ts",
        "apps/web/src/hooks/workspace/useClientChatDisputesModel.ts",
        "apps/web/src/hooks/workspace/usePaymentReportModel.ts",
        "apps/web/src/hooks/workspace/useRemitterOrdersModel.ts",
    )
    for path in hook_paths:
        source = _read(path)
        assert "useStableIdempotencyKeys" in source
        assert "getIdempotencyKey(" in source
        assert "clearIdempotencyKey(" in source
        assert "Date.now()" not in _idempotency_lines(source)


def test_sensitive_action_state_is_scoped_away_from_one_global_busy_flag() -> None:
    business_chat = "\n".join(
        _read(path)
        for path in (
            "apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts",
            "apps/web/src/hooks/business-mini-app/chat/useBusinessChatAttachments.ts",
            "apps/web/src/hooks/business-mini-app/chat/useBusinessChatComposer.ts",
            "apps/web/src/hooks/business-mini-app/chat/useBusinessPaymentShareActions.ts",
            "apps/web/src/hooks/business-mini-app/chat/useBusinessChatOrderActions.ts",
        )
    )
    business_credits = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    business_orders = _read("apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts")
    business_payment_methods = _read("apps/web/src/hooks/business-mini-app/useBusinessPaymentMethodsModel.ts")
    client_action_state = _read("apps/web/src/hooks/workspace/useClientActionState.ts")
    client_chat_composer = _read("apps/web/src/hooks/workspace/useClientChatComposerModel.ts")
    client_workspace_state = _read("apps/web/src/hooks/workspace/useClientWorkspaceState.ts")

    client_action_surface = "\n".join((client_action_state, client_chat_composer))
    for expected_state in (
        "sendingChatMessage",
        "uploadingChatAttachment",
        "generatingCreditPayment",
        "verifyingCreditTx",
        "businessOrderAction",
        "deletingPaymentMethodId",
        "savingPaymentMethodId",
    ):
        joined = "\n".join((business_chat, business_credits, business_orders, business_payment_methods))
        assert expected_state in joined

    assert "useClientActionState" in client_workspace_state
    for expected_state in (
        "creatingOrder",
        "extendingOrderId",
        "cancellingOrderId",
        "uploadingPaymentEvidence",
        "submittingPaymentReport",
        "sendingChatMessage",
    ):
        assert expected_state in client_action_surface
