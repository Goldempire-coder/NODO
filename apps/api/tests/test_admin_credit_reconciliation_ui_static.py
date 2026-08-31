from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_credit_detail_is_loaded_on_demand_with_concrete_dtos() -> None:
    api = _read("apps/web/src/api/admin.ts")
    model = _read("apps/web/src/hooks/admin-web/useAdminCreditPurchasesModel.ts")
    types = _read("apps/web/src/types/credits.ts")

    assert "getAdminCreditPurchaseDetail" in api
    assert "AdminCreditPurchaseSummary" in types
    assert "AdminCreditPurchaseDetail" in types
    assert "getAdminCreditPurchaseDetail(request, purchase.id)" in model
    assert "setInterval" not in model


def test_admin_credit_screen_uses_masked_reconciliation_and_scoped_scroll() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminCreditScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert "onchain_evidence" in screen
    assert "tx_hash_masked" in screen
    assert "destination_wallet_masked" in screen
    assert "payer_wallet_masked" in screen
    assert "payment_contract_masked" in screen
    assert "purchase_ref_masked" in screen
    assert "payer_matches" in screen
    assert "reconciliation.warning_codes" in screen
    assert "admin-web-credit-detail-scroll" in screen
    assert ".admin-web-credit-detail-scroll" in css
    assert "overflow-y: auto" in css
    assert "destination_wallet_address" not in screen
    assert "onchain_payer_address" not in screen
    assert "payment_contract_address" not in screen
    assert "onchain_purchase_ref" not in screen
    assert "tx_to_address" not in screen


def test_admin_credit_review_removes_purchase_when_status_leaves_applied_filter() -> None:
    model = _read("apps/web/src/hooks/admin-web/useAdminCreditPurchasesModel.ts")

    assert "purchaseMatchesStatusFilter" in model
    assert "creditPurchasesQueryRef.current" in model
    assert "current.filter((item) => item.id !== data.purchase.id)" in model
    assert "setSelectedCreditPurchaseDetail(data)" in model
    assert "await loadCreditPurchases" not in model


def test_admin_credit_review_reason_copy_is_explicitly_required() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminCreditScreens.tsx")

    assert 'label="Razon obligatoria para revisar compra de creditos"' in screen
    assert 'placeholder="Indica el motivo operativo antes de aprobar o rechazar"' in screen


def test_admin_credit_review_status_filter_uses_known_select_options() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminCreditScreens.tsx")

    assert "CREDIT_PURCHASE_STATUS_OPTIONS" in screen
    assert "<select value={model.creditFilter}" in screen
    assert '<span>Estado</span>' in screen
    assert 'value: "pending_manual_review"' in screen
    assert 'value: "pending_payment"' in screen
    assert 'value: "pending_onchain_confirmation"' in screen
    assert 'value: "credited"' in screen
    assert '<input value={model.creditFilter}' not in screen
