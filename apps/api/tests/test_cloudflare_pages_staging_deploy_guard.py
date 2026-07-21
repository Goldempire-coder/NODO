from __future__ import annotations

import importlib.util
from pathlib import Path

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
