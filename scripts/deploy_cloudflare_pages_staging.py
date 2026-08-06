"""Guarded Cloudflare Pages staging build/deploy for NODO Web.

This script is intentionally narrow: it validates the public build environment,
builds the static Next.js app, verifies the generated bundle points at the
staging API, and only deploys when explicitly confirmed.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
WEB_OUT = ROOT / "apps" / "web" / "out"
DEFAULT_PROJECT_NAME = "nodo-staging"
DEFAULT_BRANCH = "staging"
EMPTY_API_FALLBACK_SIGNATURE = 'case"NEXT_PUBLIC_API_BASE_URL":return""'


class GuardrailError(RuntimeError):
    """Raised when a staging deploy guardrail fails."""


def _required(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise GuardrailError(f"Missing required public build env: {key}")
    return value.rstrip("/")


def _https_url(key: str, value: str):
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise GuardrailError(f"{key} must be an absolute https URL")
    return parsed


def validate_public_env(env: dict[str, str]) -> dict[str, str]:
    api_base_url = _required(env, "NEXT_PUBLIC_API_BASE_URL")
    app_url = _required(env, "NEXT_PUBLIC_APP_URL")
    app_env = _required(env, "NEXT_PUBLIC_APP_ENV")

    api = _https_url("NEXT_PUBLIC_API_BASE_URL", api_base_url)
    app = _https_url("NEXT_PUBLIC_APP_URL", app_url)

    api_host = (api.hostname or "").lower()
    if api_host in {"localhost", "127.0.0.1"}:
        raise GuardrailError("NEXT_PUBLIC_API_BASE_URL must not point to localhost for staging")
    if api_host.endswith(".pages.dev"):
        raise GuardrailError("NEXT_PUBLIC_API_BASE_URL must point to the API, not Cloudflare Pages")
    if app_env != "staging":
        raise GuardrailError("NEXT_PUBLIC_APP_ENV must be staging")
    if not (app.hostname or "").lower().endswith("pages.dev"):
        raise GuardrailError("NEXT_PUBLIC_APP_URL must point to the Cloudflare Pages staging app")

    return {
        "NEXT_PUBLIC_API_BASE_URL": api_base_url,
        "NEXT_PUBLIC_APP_URL": app_url,
        "NEXT_PUBLIC_APP_ENV": app_env,
        "api_host": api_host,
        "app_host": app.hostname or "",
    }


def _public_api_request(
    api_base_url: str,
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 10,
) -> tuple[int, object, bytes]:
    url = f"{api_base_url.rstrip('/')}{path}"
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        payload = exc.read() if exc.fp else b""
        return exc.code, exc.headers, payload
    except urllib.error.URLError as exc:
        raise GuardrailError(f"Public API is unreachable: {exc.reason}") from exc


def _header(headers: object, name: str) -> str:
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return ""
    return str(getter(name, "") or "")


def _ensure_not_railway_fallback(headers: object) -> None:
    if _header(headers, "x-railway-fallback"):
        raise GuardrailError("Public API returned Railway fallback instead of the NODO service")


def _ensure_json(headers: object, path: str) -> None:
    content_type = _header(headers, "content-type").lower()
    if "json" not in content_type:
        raise GuardrailError(f"Public API {path} did not return JSON")


def verify_public_api(api_base_url: str, app_url: str) -> None:
    for path in ("/health", "/api/v1/version"):
        status, headers, _body = _public_api_request(api_base_url, path)
        _ensure_not_railway_fallback(headers)
        if status != 200:
            raise GuardrailError(f"Public API {path} returned {status}")
        _ensure_json(headers, path)

    status, headers, _body = _public_api_request(
        api_base_url,
        "/api/v1/auth/telegram",
        method="POST",
        body=b'{"init_data":"invalid","surface":"business"}',
        headers={
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": app_url.rstrip("/"),
        },
    )
    _ensure_not_railway_fallback(headers)
    if status not in {400, 401, 422}:
        raise GuardrailError(f"Public API auth smoke returned unexpected status {status}")
    _ensure_json(headers, "/api/v1/auth/telegram")
    allowed_origin = _header(headers, "access-control-allow-origin")
    if allowed_origin not in {"*", app_url.rstrip("/")}:
        raise GuardrailError("Public API auth smoke did not expose the expected CORS origin")


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    resolved = _resolve_command(command)
    print("+ " + " ".join(command))
    subprocess.run(resolved, cwd=ROOT, env=env, check=True)


def _resolve_command(command: list[str]) -> list[str]:
    executable = shutil.which(command[0])
    if executable:
        return [executable, *command[1:]]
    if os.name == "nt":
        for suffix in (".cmd", ".exe", ".bat"):
            executable = shutil.which(f"{command[0]}{suffix}")
            if executable:
                return [executable, *command[1:]]
    raise GuardrailError(f"Command not found: {command[0]}")


def build_web() -> None:
    _run(["pnpm", "--filter", "@nodo/web", "build"], env=os.environ.copy())


def verify_static_export(api_base_url: str, out_dir: Path = WEB_OUT) -> None:
    static_dir = out_dir / "_next" / "static"
    if not static_dir.is_dir():
        raise GuardrailError(f"Static export not found: {static_dir}")

    js_files = list(static_dir.rglob("*.js"))
    if not js_files:
        raise GuardrailError("Static export has no JavaScript chunks to verify")

    found_api_url = False
    for js_file in js_files:
        text = js_file.read_text(encoding="utf-8", errors="ignore")
        if api_base_url in text:
            found_api_url = True
        if EMPTY_API_FALLBACK_SIGNATURE in text:
            raise GuardrailError(
                "Static bundle still contains an empty NEXT_PUBLIC_API_BASE_URL fallback"
            )

    if not found_api_url:
        raise GuardrailError("Static bundle does not contain the expected NEXT_PUBLIC_API_BASE_URL")


def require_clean_git_tree() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.stdout.strip():
        raise GuardrailError("Refusing to deploy from a dirty git working tree")


def deploy_to_cloudflare(project_name: str, branch: str, wrangler_command: str) -> None:
    wrangler = shlex.split(wrangler_command, posix=False)
    if not wrangler:
        raise GuardrailError("Wrangler command cannot be empty")
    _run(
        [
            *wrangler,
            "pages",
            "deploy",
            str(WEB_OUT),
            "--project-name",
            project_name,
            "--branch",
            branch,
        ],
        env=os.environ.copy(),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and optionally deploy NODO Web staging safely.")
    parser.add_argument("--deploy", action="store_true", help="Deploy to Cloudflare Pages after build.")
    parser.add_argument(
        "--confirm-staging-deploy",
        action="store_true",
        help="Required with --deploy to prevent accidental provider changes.",
    )
    parser.add_argument("--skip-build", action="store_true", help="Verify existing apps/web/out without rebuilding.")
    parser.add_argument(
        "--project-name",
        default=os.environ.get("CLOUDFLARE_PAGES_PROJECT_NAME", DEFAULT_PROJECT_NAME),
    )
    parser.add_argument("--branch", default=os.environ.get("CLOUDFLARE_PAGES_BRANCH", DEFAULT_BRANCH))
    parser.add_argument(
        "--wrangler-command",
        default=os.environ.get("WRANGLER_COMMAND", "pnpm dlx wrangler"),
        help="Command prefix used for Cloudflare deploy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        public_env = validate_public_env(dict(os.environ))
        print(
            "staging public env guard: PASS "
            f"api_host={public_env['api_host']} app_host={public_env['app_host']}"
        )
        verify_public_api(public_env["NEXT_PUBLIC_API_BASE_URL"], public_env["NEXT_PUBLIC_APP_URL"])
        print("public api smoke guard: PASS")
        if not args.skip_build:
            build_web()
        verify_static_export(public_env["NEXT_PUBLIC_API_BASE_URL"])
        print("static export guard: PASS")

        if args.deploy:
            if not args.confirm_staging_deploy:
                raise GuardrailError("--deploy requires --confirm-staging-deploy")
            require_clean_git_tree()
            deploy_to_cloudflare(args.project_name, args.branch, args.wrangler_command)
            print(f"cloudflare pages deploy requested: project={args.project_name} branch={args.branch}")
        else:
            print("deploy skipped: build verified only")
    except GuardrailError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
