from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_admin_credit_transactions_register_has_dedicated_view_scroll_and_pagination() -> None:
    admin_types = _read("apps/web/src/hooks/admin-web/adminWebTypes.ts")
    credit_types = _read("apps/web/src/hooks/admin-web/adminCreditsTypes.ts")
    model = _read("apps/web/src/hooks/useAdminWebModel.ts")
    api = _read("apps/web/src/api/admin.ts")
    screen = _read("apps/web/src/screens/admin-web/AdminCreditScreens.tsx")
    css = _read("apps/web/src/app/admin-web.css")

    assert '"credit-transactions"' in admin_types
    assert '"credit-transactions"' in credit_types
    assert "loadCreditTransactions" in model
    assert "Registro NODO" in model
    assert "listAdminCreditTransactions" in api
    assert "/api/v1/admin/credit-transactions" in api
    assert "dateTimeLocalToIso" in api
    assert ".toISOString()" in api
    assert "CreditTransactions" in screen
    assert "admin-web-credit-transactions-panel" in screen
    assert "admin-web-credit-transactions-list-scroll" in screen
    assert 'aria-label="Registro de transacciones de creditos admin"' in screen
    assert "creditTransactionsNextCursor" in screen
    assert "loadMoreCreditTransactions" in screen
    assert ".admin-web-credit-transactions-panel" in css
    assert ".admin-web-credit-transactions-list-scroll" in css
    assert ".admin-web-credit-transactions-list-scroll:focus-visible" in css
    assert ".admin-web-credit-transactions-list-scroll .admin-web-table th" in css
    assert "setInterval" not in _read("apps/web/src/hooks/admin-web/useAdminCreditTransactionsModel.ts")


def test_admin_credit_transactions_ui_uses_summary_filters_and_masked_evidence() -> None:
    screen = _read("apps/web/src/screens/admin-web/AdminCreditScreens.tsx")
    types = _read("apps/web/src/types/credits.ts")

    assert "AdminCreditTransactionSummary" in types
    assert "AdminCreditTransactionItem" in types
    assert "Ingresos confirmados" in screen
    assert "Creditos confirmados" in screen
    assert "Pendientes" in screen
    assert "En revision" in screen
    assert "Descartados" in screen
    assert "tx_hash_masked" in screen
    assert "payer_wallet_masked" in screen
    assert "payment_contract_masked" in screen
    assert "tx_hash:" not in screen
    assert "onchain_payer_address" not in screen
    assert "payment_contract_address" not in screen
    assert "onchain_purchase_ref" not in screen
