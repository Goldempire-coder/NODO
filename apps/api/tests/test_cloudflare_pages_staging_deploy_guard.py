from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "deploy_cloudflare_pages_staging.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("deploy_cloudflare_pages_staging", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _valid_env() -> dict[str, str]:
    return {
        "NEXT_PUBLIC_API_BASE_URL": "https://nodo-api-production.up.railway.app",
        "NEXT_PUBLIC_APP_URL": "https://nodo-staging.pages.dev",
        "NEXT_PUBLIC_APP_ENV": "staging",
    }


def test_staging_deploy_guard_requires_public_api_url() -> None:
    module = _load_module()
    env = _valid_env()
    env.pop("NEXT_PUBLIC_API_BASE_URL")

    with pytest.raises(module.GuardrailError, match="NEXT_PUBLIC_API_BASE_URL"):
        module.validate_public_env(env)


def test_staging_deploy_guard_rejects_cloudflare_pages_as_api_url() -> None:
    module = _load_module()
    env = _valid_env()
    env["NEXT_PUBLIC_API_BASE_URL"] = "https://nodo-staging.pages.dev"

    with pytest.raises(module.GuardrailError, match="not Cloudflare Pages"):
        module.validate_public_env(env)


def test_staging_deploy_guard_requires_staging_app_env() -> None:
    module = _load_module()
    env = _valid_env()
    env["NEXT_PUBLIC_APP_ENV"] = "production"

    with pytest.raises(module.GuardrailError, match="must be staging"):
        module.validate_public_env(env)


def test_staging_deploy_guard_accepts_expected_staging_public_env() -> None:
    module = _load_module()

    result = module.validate_public_env(_valid_env())

    assert result["NEXT_PUBLIC_API_BASE_URL"] == "https://nodo-api-production.up.railway.app"
    assert result["api_host"] == "nodo-api-production.up.railway.app"
    assert result["app_host"] == "nodo-staging.pages.dev"


class _FakeHeaders(dict[str, str]):
    def get(self, key: str, default: str | None = None) -> str | None:
        return super().get(key.lower(), default)


class _FakeResponse:
    def __init__(self, status: int = 200, headers: dict[str, str] | None = None, body: bytes = b'{"data":{}}') -> None:
        self.status = status
        self.headers = _FakeHeaders({key.lower(): value for key, value in (headers or {}).items()})
        self._body = body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_staging_api_smoke_rejects_railway_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()

    def fake_urlopen(request: Any, timeout: float) -> _FakeResponse:
        return _FakeResponse(status=404, headers={"x-railway-fallback": "1"}, body=b"")

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(module.GuardrailError, match="Railway fallback"):
        module.verify_public_api("https://nodo-api-production.up.railway.app", "https://nodo-staging.pages.dev")


def test_staging_api_smoke_requires_cors_on_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    calls: list[str] = []

    def fake_urlopen(request: Any, timeout: float) -> _FakeResponse:
        calls.append(request.full_url)
        if request.full_url.endswith("/api/v1/auth/telegram"):
            return _FakeResponse(status=401, headers={"content-type": "application/json"}, body=b'{"error":{"code":"BAD_AUTH"}}')
        return _FakeResponse(status=200, headers={"content-type": "application/json"}, body=b'{"data":{}}')

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(module.GuardrailError, match="CORS"):
        module.verify_public_api("https://nodo-api-production.up.railway.app", "https://nodo-staging.pages.dev")
    assert calls[-1].endswith("/api/v1/auth/telegram")


def test_staging_api_smoke_accepts_healthy_api_with_auth_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    calls: list[tuple[str, str]] = []

    def fake_urlopen(request: Any, timeout: float) -> _FakeResponse:
        method = request.get_method()
        calls.append((method, request.full_url))
        if request.full_url.endswith("/api/v1/auth/telegram"):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                _FakeHeaders({"content-type": "application/json", "access-control-allow-origin": "https://nodo-staging.pages.dev"}),
                None,
            )
        return _FakeResponse(status=200, headers={"content-type": "application/json"}, body=b'{"data":{}}')

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    module.verify_public_api("https://nodo-api-production.up.railway.app", "https://nodo-staging.pages.dev")

    assert calls == [
        ("GET", "https://nodo-api-production.up.railway.app/health"),
        ("GET", "https://nodo-api-production.up.railway.app/api/v1/version"),
        ("POST", "https://nodo-api-production.up.railway.app/api/v1/auth/telegram"),
    ]


def test_static_export_guard_requires_expected_api_url(tmp_path: Path) -> None:
    module = _load_module()
    chunk_dir = tmp_path / "_next" / "static" / "chunks"
    chunk_dir.mkdir(parents=True)
    (chunk_dir / "app.js").write_text('case"NEXT_PUBLIC_API_BASE_URL":return"https://wrong.example.test"', encoding="utf-8")

    with pytest.raises(module.GuardrailError, match="does not contain"):
        module.verify_static_export("https://nodo-api-production.up.railway.app", tmp_path)


def test_static_export_guard_rejects_empty_api_fallback(tmp_path: Path) -> None:
    module = _load_module()
    chunk_dir = tmp_path / "_next" / "static" / "chunks"
    chunk_dir.mkdir(parents=True)
    (chunk_dir / "app.js").write_text('case"NEXT_PUBLIC_API_BASE_URL":return""', encoding="utf-8")

    with pytest.raises(module.GuardrailError, match="empty NEXT_PUBLIC_API_BASE_URL"):
        module.verify_static_export("https://nodo-api-production.up.railway.app", tmp_path)


def test_run_resolves_windows_cmd_shims(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    calls: list[list[str]] = []

    def fake_which(command: str) -> str | None:
        if command == "pnpm.cmd":
            return "C:/tools/pnpm.cmd"
        return None

    def fake_run(command: list[str], **kwargs) -> None:
        calls.append(command)

    monkeypatch.setattr(module.shutil, "which", fake_which)
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.os, "name", "nt")

    module._run(["pnpm", "--version"])

    assert calls == [["C:/tools/pnpm.cmd", "--version"]]
