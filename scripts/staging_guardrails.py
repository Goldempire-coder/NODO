from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from local_hardening_common import load_env_file, write_json


SECRET_KEY_MARKERS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "DATABASE_URL",
    "REDIS_URL",
    "SERVICE_ROLE",
    "JWT",
    "KEY",
)
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{12,120}$")


class StagingGuardrailError(RuntimeError):
    pass


@dataclass(frozen=True)
class StagingGuardrails:
    env_file: Path
    env: dict[str, str]
    run_id: str | None = None


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_RE.fullmatch(run_id):
        raise StagingGuardrailError("run_id must be 12-120 chars and contain only letters, numbers, _, ., :, or -")


def _split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _host(value: str) -> str:
    parsed = urlparse(value)
    return (parsed.hostname or "").lower()


def _normalized_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return value.rstrip("/").lower()
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def _target_contains_project_id(target: str, project_id: str) -> bool:
    if not target or not project_id:
        return False
    lowered_target = target.lower()
    lowered_project = project_id.lower()
    host = _host(target)
    host_labels = set(host.split(".")) if host else set()
    return lowered_project in host_labels or lowered_project in lowered_target.split("/")


def _require_exact_host_allowlist(*, value: str, env: dict[str, str], env_key: str, label: str) -> str:
    host = _host(value)
    if not host:
        raise StagingGuardrailError(f"{label} host is required")
    allowlist = _split_csv(env.get(env_key))
    if not allowlist:
        raise StagingGuardrailError(f"{env_key} is required")
    if host not in allowlist:
        raise StagingGuardrailError(f"{label} host is not in {env_key}")
    return host


def redact_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    upper_key = key.upper()
    if any(marker in upper_key for marker in SECRET_KEY_MARKERS):
        return "[REDACTED]"
    if value.startswith(("postgres://", "postgresql://", "redis://", "rediss://")):
        return "[REDACTED]"
    return value


def redact_mapping(values: dict[str, Any]) -> dict[str, Any]:
    return {key: redact_value(key, value) for key, value in values.items()}


def redact_text(value: str) -> str:
    redacted = value
    for key, env_value in os.environ.items():
        if not env_value or len(env_value) < 8:
            continue
        if any(marker in key.upper() for marker in SECRET_KEY_MARKERS):
            redacted = redacted.replace(env_value, "[REDACTED]")
    return redacted


def require_staging_guardrails(
    *,
    env_file: Path,
    mutating: bool = False,
    confirm_staging: bool = False,
    run_id: str | None = None,
    api_base_url: str | None = None,
) -> StagingGuardrails:
    env = load_env_file(env_file)
    if run_id:
        validate_run_id(run_id)

    app_env = env.get("APP_ENV", "").strip().lower()
    if app_env != "staging":
        raise StagingGuardrailError("Refusing non-staging env: APP_ENV must be staging")
    if env.get("NODO_ENVIRONMENT_KIND") != "staging":
        raise StagingGuardrailError("Refusing staging tooling without NODO_ENVIRONMENT_KIND=staging")
    if env.get("NODO_STAGING_VALIDATION") != "1":
        raise StagingGuardrailError("Refusing staging tooling without NODO_STAGING_VALIDATION=1")
    staging_project_id = env.get("NODO_STAGING_PROJECT_ID", "").strip().lower()
    if not staging_project_id:
        raise StagingGuardrailError("NODO_STAGING_PROJECT_ID is required")
    production_project_id = env.get("NODO_PRODUCTION_PROJECT_ID", "").strip().lower()
    if production_project_id and production_project_id == staging_project_id:
        raise StagingGuardrailError("NODO_PRODUCTION_PROJECT_ID must not match NODO_STAGING_PROJECT_ID")

    database_url = env.get("DATABASE_URL", "")
    _require_exact_host_allowlist(
        value=database_url,
        env=env,
        env_key="NODO_STAGING_DB_HOST_ALLOWLIST",
        label="DATABASE_URL",
    )
    if production_project_id and _target_contains_project_id(database_url, production_project_id):
        raise StagingGuardrailError("DATABASE_URL targets NODO_PRODUCTION_PROJECT_ID")

    api_url = api_base_url or env.get("NODO_STAGING_API_BASE_URL", "")
    if api_url:
        _require_exact_host_allowlist(
            value=api_url,
            env=env,
            env_key="NODO_STAGING_API_HOST_ALLOWLIST",
            label="API base URL",
        )
        if production_project_id and _target_contains_project_id(api_url, production_project_id):
            raise StagingGuardrailError("API base URL targets NODO_PRODUCTION_PROJECT_ID")

    supabase_url = env.get("SUPABASE_URL", "")
    if supabase_url:
        expected_supabase_url = env.get("NODO_STAGING_SUPABASE_URL", "")
        if not expected_supabase_url:
            raise StagingGuardrailError("NODO_STAGING_SUPABASE_URL is required when SUPABASE_URL is set")
        if _normalized_url(supabase_url) != _normalized_url(expected_supabase_url):
            raise StagingGuardrailError("SUPABASE_URL must exactly match NODO_STAGING_SUPABASE_URL")
        if not _target_contains_project_id(supabase_url, staging_project_id):
            raise StagingGuardrailError("SUPABASE_URL does not match NODO_STAGING_PROJECT_ID")
        if production_project_id and _target_contains_project_id(supabase_url, production_project_id):
            raise StagingGuardrailError("SUPABASE_URL targets NODO_PRODUCTION_PROJECT_ID")

    if mutating:
        if not confirm_staging:
            raise StagingGuardrailError("Mutating staging actions require --confirm-staging")
        if run_id and env.get("STAGING_VALIDATION_ACK") != run_id:
            raise StagingGuardrailError("Mutating staging actions require STAGING_VALIDATION_ACK to match --run-id")

    return StagingGuardrails(env_file=env_file, env=env, run_id=run_id)


def guardrail_payload(guardrails: StagingGuardrails) -> dict[str, Any]:
    return {
        "env_file": str(guardrails.env_file),
        "run_id": guardrails.run_id,
        "env": redact_mapping(
            {
                "APP_ENV": guardrails.env.get("APP_ENV"),
                "NODO_ENVIRONMENT_KIND": guardrails.env.get("NODO_ENVIRONMENT_KIND"),
                "NODO_STAGING_VALIDATION": guardrails.env.get("NODO_STAGING_VALIDATION"),
                "NODO_STAGING_PROJECT_ID": guardrails.env.get("NODO_STAGING_PROJECT_ID"),
                "NODO_PRODUCTION_PROJECT_ID": guardrails.env.get("NODO_PRODUCTION_PROJECT_ID"),
                "DATABASE_URL": guardrails.env.get("DATABASE_URL"),
                "REDIS_URL": guardrails.env.get("REDIS_URL"),
                "NODO_STAGING_DB_HOST_ALLOWLIST": guardrails.env.get("NODO_STAGING_DB_HOST_ALLOWLIST"),
                "NODO_STAGING_API_HOST_ALLOWLIST": guardrails.env.get("NODO_STAGING_API_HOST_ALLOWLIST"),
                "SUPABASE_URL": guardrails.env.get("SUPABASE_URL"),
                "NODO_STAGING_SUPABASE_URL": guardrails.env.get("NODO_STAGING_SUPABASE_URL"),
            }
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--api-base-url", default=None)
    parser.add_argument("--mutating", action="store_true")
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    try:
        guardrails = require_staging_guardrails(
            env_file=Path(args.env_file),
            mutating=args.mutating,
            confirm_staging=args.confirm_staging,
            run_id=args.run_id,
            api_base_url=args.api_base_url,
        )
        payload = {"phase": "staging_guardrails", "ok": True, "guardrails": guardrail_payload(guardrails), "exit_code": 0}
    except Exception as exc:
        payload = {
            "phase": "staging_guardrails",
            "ok": False,
            "error": {"type": type(exc).__name__, "message": redact_text(str(exc))},
            "exit_code": 1,
        }
    if args.output:
        write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
