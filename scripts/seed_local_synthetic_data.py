from __future__ import annotations

import argparse
import time
from pathlib import Path

from local_hardening_common import DEFAULT_ENV_FILE, write_json
from stress_local import LocalStress


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--businesses", type=int, default=2)
    parser.add_argument("--orders", type=int, default=2)
    parser.add_argument("--output", default="evidence/slice_runs/slice_11_local_seed.json")
    args = parser.parse_args()
    payload = LocalStress(
        env_file=Path(args.env_file),
        run_id=f"seed{int(time.time())}",
        profile="initial",
        cap_businesses=args.businesses,
        cap_orders=args.orders,
    ).run_stress()
    payload["phase"] = "local_seed"
    write_json(Path(args.output), payload)
    print(payload)
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
