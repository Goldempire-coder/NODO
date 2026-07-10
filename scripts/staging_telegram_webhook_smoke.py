from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx

from local_hardening_common import add_api_path, write_json
from staging_guardrails import guardrail_payload, redact_text, require_staging_guardrails

add_api_path()
from app.routes.telegram_bot import telegram_webhook_secret  # noqa: E402


def _chat_hash(chat_id: str) -> str:
    return hashlib.sha256(chat_id.encode("utf-8")).hexdigest()[:12]


def run_reject_only(*, base_url: str, bot: str) -> dict:
    path = "/api/v1/business-intake/telegram/webhook/invalid-staging-smoke-secret" if bot == "business-intake" else "/api/v1/telegram/webhook/invalid-staging-smoke-secret"
    response = httpx.post(
        f"{base_url.rstrip('/')}{path}",
        json={"update_id": int(time.time()), "message": {"chat": {"id": 1}, "from": {"id": 1}, "text": "/start"}},
        timeout=10.0,
    )
    return {
        "mode": "reject_only",
        "bot": bot,
        "status_code": response.status_code,
        "expected_status_code": 403,
        "passed": response.status_code == 403,
    }


def run_valid_test_chat(*, base_url: str, bot: str, token: str, test_chat_id: str) -> dict:
    secret = telegram_webhook_secret(token)
    path = f"/api/v1/business-intake/telegram/webhook/{secret}" if bot == "business-intake" else f"/api/v1/telegram/webhook/{secret}"
    response = httpx.post(
        f"{base_url.rstrip('/')}{path}",
        json={
            "update_id": int(time.time()),
            "message": {
                "message_id": 1,
                "chat": {"id": int(test_chat_id), "type": "private"},
                "from": {"id": int(test_chat_id), "first_name": "Staging"},
                "text": "/start",
            },
        },
        timeout=10.0,
    )
    return {
        "mode": "valid_test_chat",
        "bot": bot,
        "test_chat_hash": _chat_hash(test_chat_id),
        "status_code": response.status_code,
        "passed": response.status_code < 500,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--bot", choices=["client", "business-intake"], default="business-intake")
    parser.add_argument("--allow-send", action="store_true")
    parser.add_argument("--test-chat-id", default=None)
    args = parser.parse_args()
    guardrails = require_staging_guardrails(env_file=Path(args.env_file), api_base_url=args.base_url)
    base_url = args.base_url or guardrails.env.get("NODO_STAGING_API_BASE_URL")
    if not base_url:
        raise SystemExit("NODO_STAGING_API_BASE_URL or --base-url is required")
    payload = {
        "slice": "slice_17A_staging_validation_tooling",
        "phase": "staging_telegram_webhook_smoke",
        "guardrails": guardrail_payload(guardrails),
        "result": {},
        "failures": [],
        "exit_code": 0,
    }
    try:
        if args.allow_send:
            if not args.test_chat_id:
                raise RuntimeError("--test-chat-id is required with --allow-send")
            token_key = "BUSINESS_INTAKE_BOT_TOKEN" if args.bot == "business-intake" else "BOT_TOKEN"
            token = guardrails.env.get(token_key)
            if not token:
                raise RuntimeError(f"{token_key} is required")
            payload["result"] = run_valid_test_chat(base_url=base_url, bot=args.bot, token=token, test_chat_id=args.test_chat_id)
        else:
            payload["result"] = run_reject_only(base_url=base_url, bot=args.bot)
        if not payload["result"]["passed"]:
            payload["failures"].append("telegram_smoke_failed")
    except Exception as exc:
        payload["failures"].append(f"{type(exc).__name__}:{redact_text(str(exc))}")
    payload["exit_code"] = 1 if payload["failures"] else 0
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
