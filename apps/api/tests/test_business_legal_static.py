from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_business_legal_acceptance_is_separate_from_credit_payment_runtime() -> None:
    routes = _read("apps/api/app/modules/legal/routes.py")
    service = _read("apps/api/app/modules/legal/service.py")
    credit_routes = _read("apps/api/app/modules/credits/routes.py")
    migration = _read("database/migrations/0061_business_legal_acceptances.up.sql")
    main = _read("apps/api/app/main.py")

    assert "/business/legal/requirements" in routes
    assert "/business/legal/acceptances" in routes
    assert "BUSINESS_LEGAL_CONFIRMATION" in service
    assert "business_legal_terms_accepted" in service
    assert "business_legal_acceptances" in migration
    assert "on conflict (business_id, user_id, document_set, document_version)" in _read(
        "apps/api/app/modules/legal/postgres_repository.py"
    )
    assert "business_legal_acceptance_repository" in main
    assert "_legal_service(request).require_business_credit_terms(user=user)" in credit_routes
    assert "def business_pending_contract_credit_purchase" in credit_routes
    assert credit_routes.index('def business_pending_contract_credit_purchase') < credit_routes.index(
        'def create_credit_handoff'
    )


def test_business_legal_terms_are_gated_in_frontend_without_checkout_copy_sprawl() -> None:
    model = _read("apps/web/src/hooks/useBusinessMiniAppModel.ts")
    credits_model = _read("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts")
    views = _read("apps/web/src/constants/businessViews.ts")
    screens = _read("apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx")
    settings = _read("apps/web/src/screens/business-app/BusinessSettingsScreen.tsx")
    api = _read("apps/web/src/api/legal.ts")

    assert "business-credit-terms" in views
    assert "BusinessCreditTermsScreen" in screens
    assert "ensureBusinessCreditTermsAccepted" in model
    assert "acceptBusinessCreditTerms" in model
    assert "acceptBusinessLegalTerms" in api
    assert "/api/v1/business/legal/requirements" in api
    assert "/api/v1/business/legal/acceptances" in api
    assert "Acepta los terminos de creditos antes de comprar." in model
    assert "skipLegalCheck" in credits_model
    assert "NODO nunca pide frase secreta ni clave privada." in settings
    assert "No se canjean, retiran ni transfieren." in settings
