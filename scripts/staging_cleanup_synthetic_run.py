from __future__ import annotations

import argparse
import json
from pathlib import Path

from cleanup_synthetic_run import cleanup
from local_hardening_common import write_json
from staging_guardrails import guardrail_payload, redact_text, require_staging_guardrails


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()
    guardrails = require_staging_guardrails(
        env_file=Path(args.env_file),
        mutating=bool(args.apply),
        confirm_staging=args.confirm_staging,
        run_id=args.run_id,
    )
    payload = {
        "slice": "slice_17A_staging_validation_tooling",
        "phase": "staging_cleanup_synthetic_run",
        "guardrails": guardrail_payload(guardrails),
        "mode": "apply" if args.apply else "dry_run",
        "cleanup": {},
        "failures": [],
        "exit_code": 0,
    }
    try:
        payload["cleanup"] = cleanup(env_file=Path(args.env_file), run_id=args.run_id, execute=bool(args.apply))
    except Exception as exc:
        payload["failures"].append(f"{type(exc).__name__}:{redact_text(str(exc))}")
    payload["exit_code"] = 1 if payload["failures"] else 0
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
