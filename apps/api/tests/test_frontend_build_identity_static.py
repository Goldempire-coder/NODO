from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
IDENTITY_HELPER = ROOT / "apps" / "web" / "src" / "lib" / "buildIdentity.ts"
VERSION_ROUTE = ROOT / "apps" / "web" / "src" / "app" / "version.json" / "route.ts"
HEADERS = ROOT / "apps" / "web" / "public" / "_headers"
DEPLOY_GUARD = ROOT / "scripts" / "deploy_cloudflare_pages_staging.py"
INFRA_REPORT = (
    ROOT
    / "control_plane"
    / "09_SLICES"
    / "slice_47G_preproduction_security_launch_gate"
    / "INFRA_REAL_SECURITY_47G4.md"
)


def _load_deploy_guard():
    spec = importlib.util.spec_from_file_location("deploy_cloudflare_pages_staging", DEPLOY_GUARD)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frontend_exports_allowlisted_build_identity() -> None:
    helper = IDENTITY_HELPER.read_text(encoding="utf-8")
    route = VERSION_ROUTE.read_text(encoding="utf-8")

    assert 'service: "nodo-web"' in helper
    assert "environment" in helper
    assert "commit_sha" in helper
    assert "build_id" in helper
    assert "source" in helper
    assert "NODO_RELEASE_COMMIT_SHA" in helper
    assert "CF_PAGES_COMMIT_SHA" in helper
    assert 'dynamic = "force-static"' in route
    assert "publicBuildIdentity" in route

    forbidden = (
        "DATABASE_URL",
        "REDIS_URL",
        "SERVICE_ROLE",
        "STRIPE_SECRET",
        "PRIVATE_KEY",
        "MNEMONIC",
        "SEED_PHRASE",
        "WALLET_PRIVATE",
        "TOKEN_SECRET",
    )
    assert all(name not in helper for name in forbidden)
    assert all(name not in route for name in forbidden)


def test_frontend_version_metadata_is_not_cached() -> None:
    headers = HEADERS.read_text(encoding="utf-8")

    assert "/version.json\n  Cache-Control: no-store" in headers


def test_build_identity_gate_rejects_unknown_and_mismatch() -> None:
    module = _load_deploy_guard()
    sha = "a" * 40
    backend = {"environment": "staging", "build_id": sha}

    module.verify_matching_builds(
        {
            "service": "nodo-web",
            "environment": "staging",
            "commit_sha": sha,
            "build_id": f"staging-{sha[:7]}",
            "source": "release_env",
        },
        backend,
    )

    with pytest.raises(module.GuardrailError, match="unknown"):
        module.verify_matching_builds(
            {
                "service": "nodo-web",
                "environment": "staging",
                "commit_sha": "unknown",
                "build_id": "unknown",
                "source": "unknown",
            },
            backend,
        )

    with pytest.raises(module.GuardrailError, match="do not match"):
        module.verify_matching_builds(
            {
                "service": "nodo-web",
                "environment": "staging",
                "commit_sha": "b" * 40,
                "build_id": "staging-bbbbbbb",
                "source": "release_env",
            },
            backend,
        )

    with pytest.raises(module.GuardrailError, match="inconsistent"):
        module.verify_matching_builds(
            {
                "service": "nodo-web",
                "environment": "staging",
                "commit_sha": sha,
                "build_id": "staging-wrong",
                "source": "release_env",
            },
            backend,
        )

    with pytest.raises(module.GuardrailError, match="local Git HEAD"):
        module.verify_matching_builds(
            {
                "service": "nodo-web",
                "environment": "staging",
                "commit_sha": sha,
                "build_id": "staging-aaaaaaa",
                "source": "release_env",
            },
            backend,
            "b" * 40,
        )


def test_static_export_guard_reads_only_allowlisted_identity(tmp_path: Path) -> None:
    module = _load_deploy_guard()
    api_base_url = "https://api.example.test"
    chunk_dir = tmp_path / "_next" / "static" / "chunks"
    chunk_dir.mkdir(parents=True)
    (chunk_dir / "app.js").write_text(api_base_url, encoding="utf-8")
    sha = "a" * 40
    (tmp_path / "version.json").write_text(
        (
            '{"service":"nodo-web","environment":"staging",'
            f'"commit_sha":"{sha}","build_id":"staging-aaaaaaa",'
            '"source":"release_env"}'
        ),
        encoding="utf-8",
    )

    identity = module.verify_static_export(api_base_url, tmp_path)

    assert identity == {
        "service": "nodo-web",
        "environment": "staging",
        "commit_sha": sha,
        "build_id": "staging-aaaaaaa",
        "source": "release_env",
    }

    (tmp_path / "version.json").write_text(
        '{"service":"nodo-web","environment":"staging","commit_sha":"unknown",'
        '"build_id":"unknown","source":"unknown","env":{}}',
        encoding="utf-8",
    )
    with pytest.raises(module.GuardrailError, match="unexpected schema"):
        module.verify_static_export(api_base_url, tmp_path)


def test_47g4_documents_the_frontend_backend_gate() -> None:
    report = INFRA_REPORT.read_text(encoding="utf-8")

    assert "/version.json" in report
    assert "frontend.commit_sha" in report
    assert "backend.data.build_id" in report
    assert "unknown" in report
    assert "mismatch" in report
