from __future__ import annotations

import pytest
from app.core.config import EnvValidationError, load_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient

PREVIEW = "https://review-123.nodo-staging.pages.dev"
OFFICIAL = "https://app.example.invalid"


def _env(app_env: str = "production") -> dict[str, str]:
    return {
        "APP_ENV": app_env,
        "DATABASE_URL": "postgresql://fake:fake@127.0.0.1:1/fake",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "TELEGRAM_WEB_APP_URL": OFFICIAL,
        "TELEGRAM_WELCOME_IMAGE_URL": OFFICIAL + "/welcome.jpg",
        "API_CORS_ORIGINS": OFFICIAL,
    }


def _client(env: dict[str, str]) -> TestClient:
    from app.main import _configure_middlewares

    app = FastAPI()
    app.state.settings = load_settings(env)
    _configure_middlewares(app, settings=app.state.settings)

    @app.get("/synthetic")
    def synthetic() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/synthetic",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,x-request-id",
        },
    )


@pytest.mark.parametrize(
    "regex", [None, ".*", r"^https://.*\.nodo-staging\.pages\.dev$"]
)
def test_production_rejects_preview_even_with_configured_regex(
    regex: str | None,
) -> None:
    env = _env()
    if regex is not None:
        env["API_CORS_ORIGIN_REGEX"] = regex
    client = _client(env)
    rejected = _preflight(client, PREVIEW)
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
    allowed = _preflight(client, OFFICIAL)
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == OFFICIAL
    assert "PATCH" in allowed.headers["access-control-allow-methods"]
    assert "access-control-allow-credentials" not in allowed.headers


@pytest.mark.parametrize(
    "origin", ["https://other.example.invalid", "null", "http://localhost:3000"]
)
def test_production_rejects_unlisted_origins(origin: str) -> None:
    client = _client(_env())
    assert _preflight(client, origin).status_code == 400
    response = client.get("/synthetic", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "access-control-allow-origin" not in response.headers


def test_production_without_explicit_origins_denies_browser_access() -> None:
    env = _env()
    del env["API_CORS_ORIGINS"]
    settings = load_settings(env)
    assert settings.cors_origins == []
    assert _preflight(_client(env), "http://localhost:3000").status_code == 400


@pytest.mark.parametrize("origin", ["*", PREVIEW, "https://nodo-staging.pages.dev"])
def test_production_rejects_wildcard_or_staging_allowlist(origin: str) -> None:
    env = {**_env(), "API_CORS_ORIGINS": OFFICIAL + "," + origin}
    with pytest.raises(EnvValidationError) as caught:
        load_settings(env)
    assert caught.value.missing_keys == ["API_CORS_ORIGINS"]
    assert origin not in str(caught.value)


@pytest.mark.parametrize("app_env", ["local", "dev", "development", "staging", "test"])
def test_nonproduction_keeps_preview_default(app_env: str) -> None:
    response = _preflight(_client(_env(app_env)), PREVIEW)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PREVIEW


def test_staging_regex_replaces_default_and_empty_value_disables_it() -> None:
    env = {
        **_env("staging"),
        "API_CORS_ORIGIN_REGEX": r"^https://review-[0-9]+\.example\.invalid$",
    }
    client = _client(env)
    assert _preflight(client, "https://review-123.example.invalid").status_code == 200
    assert _preflight(client, PREVIEW).status_code == 400
    assert _preflight(client, OFFICIAL).status_code == 200
    env["API_CORS_ORIGIN_REGEX"] = ""
    client = _client(env)
    assert _preflight(client, PREVIEW).status_code == 400
    assert _preflight(client, "https://review-123.example.invalid").status_code == 400
    assert _preflight(client, OFFICIAL).status_code == 200


def test_invalid_staging_regex_fails_without_echoing_its_value() -> None:
    invalid = "[synthetic-private-marker"
    with pytest.raises(EnvValidationError) as caught:
        load_settings({**_env("staging"), "API_CORS_ORIGIN_REGEX": invalid})
    assert caught.value.missing_keys == ["API_CORS_ORIGIN_REGEX"]
    assert invalid not in str(caught.value)
    assert caught.value.__suppress_context__


def test_unrecognized_environment_does_not_enable_preview_regex() -> None:
    assert (
        _preflight(
            _client({**_env("qa"), "API_CORS_ORIGIN_REGEX": ".*"}), PREVIEW
        ).status_code
        == 400
    )


@pytest.mark.parametrize("key", ["TELEGRAM_WEB_APP_URL", "TELEGRAM_WELCOME_IMAGE_URL"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_production_requires_each_telegram_url(key: str, value: str | None) -> None:
    env = _env()
    if value is None:
        del env[key]
    else:
        env[key] = value
    with pytest.raises(EnvValidationError) as caught:
        load_settings(env)
    assert caught.value.missing_keys == [key]
    assert str(caught.value) == f"Missing required environment keys: {key}"


def test_production_startup_fails_before_creating_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import main

    for key, value in _env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("TELEGRAM_WEB_APP_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_WELCOME_IMAGE_URL", raising=False)

    def forbidden_runtime(*args, **kwargs):
        pytest.fail("Runtime must not be configured with missing Telegram URLs")

    monkeypatch.setattr(main, "_new_fastapi_app", forbidden_runtime)
    with pytest.raises(EnvValidationError) as caught:
        main.create_app()
    assert caught.value.missing_keys == [
        "TELEGRAM_WEB_APP_URL",
        "TELEGRAM_WELCOME_IMAGE_URL",
    ]


@pytest.mark.parametrize("app_env", ["local", "dev", "staging", "test"])
def test_nonproduction_retains_telegram_defaults(app_env: str) -> None:
    env = _env(app_env)
    del env["TELEGRAM_WEB_APP_URL"]
    del env["TELEGRAM_WELCOME_IMAGE_URL"]
    settings = load_settings(env)
    assert settings.telegram_web_app_url == "https://nodo-staging.pages.dev"
    assert (
        settings.telegram_welcome_image_url
        == "https://nodo-staging.pages.dev/telegram-welcome.jpg?v=20260818143000"
    )


def test_explicit_production_telegram_urls_are_preserved() -> None:
    settings = load_settings({**_env(), "TELEGRAM_WEB_APP_URL": OFFICIAL + "/"})
    assert settings.telegram_web_app_url == OFFICIAL
    assert settings.telegram_welcome_image_url == OFFICIAL + "/welcome.jpg"
