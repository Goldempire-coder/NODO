"""Pre-deploy repository audit for NODO.

This script is intentionally conservative. It does not deploy, delete, move,
stage, or commit files. It only reports whether the current working tree is
safe enough to become a release candidate.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


RUNTIME_PREFIXES = (
    "apps/api/app/",
    "apps/web/src/",
    "apps/web/public/",
    "database/migrations/",
)

RUNTIME_FILES = {
    ".env.example",
    ".env.local.example",
    ".env.staging.example",
    "Dockerfile",
    "railway.json",
    "package.json",
    "pnpm-lock.yaml",
    "pytest.ini",
    "apps/web/next.config.mjs",
}

TOOLING_PREFIXES = (
    ".github/workflows/",
    "apps/api/tests/",
    "scripts/",
)

DOC_PREFIXES = (
    "control_plane/",
    "operations/",
    "governance/",
)

EVIDENCE_PREFIXES = (
    "evidence/",
)

BLOCKING_SECRET_PATTERNS = {
    "coinbase_rpc_key_in_url": re.compile(r"api\.developer\.coinbase\.com/rpc/v1/base/[A-Za-z0-9_-]{12,}"),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}

WARNING_SECRET_PATTERNS = {
    "seed_phrase_or_mnemonic_mention": re.compile(r"\b(seed phrase|mnemonic)\b", re.IGNORECASE),
    "generic_bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
}


@dataclass(frozen=True)
class GitEntry:
    status: str
    path: str


def run_git_status(root: Path) -> list[GitEntry]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    entries: list[GitEntry] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line:
            continue
        status = raw_line[:2]
        path = raw_line[3:].replace("\\", "/")
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append(GitEntry(status=status, path=path))
    return entries


def category(path: str) -> str:
    if path in RUNTIME_FILES or path.startswith(RUNTIME_PREFIXES):
        return "runtime"
    if path.startswith(TOOLING_PREFIXES):
        return "tooling"
    if path.startswith(DOC_PREFIXES):
        return "docs"
    if path.startswith(EVIDENCE_PREFIXES):
        return "evidence"
    return "other"


def is_untracked(entry: GitEntry) -> bool:
    return entry.status == "??"


def scan_files_for_secrets(root: Path, paths: list[str]) -> tuple[list[dict[str, str | int]], list[dict[str, str | int]]]:
    blockers: list[dict[str, str | int]] = []
    warnings: list[dict[str, str | int]] = []
    for path in paths:
        file_path = root / path
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            warnings.append({"path": path, "line": 0, "pattern": "read_error", "value": str(exc)})
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for name, pattern in BLOCKING_SECRET_PATTERNS.items():
                if pattern.search(line):
                    blockers.append({"path": path, "line": line_no, "pattern": name})
            for name, pattern in WARNING_SECRET_PATTERNS.items():
                if pattern.search(line):
                    warnings.append({"path": path, "line": line_no, "pattern": name})
    return blockers, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit NODO repo before preparing deploy.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    entries = run_git_status(root)
    by_category: dict[str, list[GitEntry]] = {"runtime": [], "tooling": [], "docs": [], "evidence": [], "other": []}
    for entry in entries:
        by_category[category(entry.path)].append(entry)

    untracked_runtime = [entry.path for entry in by_category["runtime"] if is_untracked(entry)]
    untracked_other_runtime_relevant = [
        entry.path
        for entry in entries
        if is_untracked(entry)
        and (
            entry.path.startswith(".github/workflows/")
            or entry.path in {"pytest.ini"}
        )
    ]
    candidate_paths = [
        entry.path
        for entry in entries
        if category(entry.path) in {"runtime", "tooling", "docs"}
        and not entry.path.endswith(".zip")
    ]
    secret_blockers, secret_warnings = scan_files_for_secrets(root, candidate_paths)

    failures: list[str] = []
    if untracked_runtime:
        failures.append("UNTRACKED_RUNTIME_FILES")
    if secret_blockers:
        failures.append("SECRET_PATTERN_FINDINGS")

    summary = {
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "counts": {name: len(items) for name, items in by_category.items()},
        "untracked_runtime_count": len(untracked_runtime),
        "untracked_runtime": untracked_runtime,
        "untracked_tooling_runtime_relevant": untracked_other_runtime_relevant,
        "secret_blockers": secret_blockers,
        "secret_warnings": secret_warnings,
        "decision": "NO_DEPLOY" if failures else "READY_FOR_VALIDATION_COMMANDS",
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"status: {summary['status']}")
        print(f"decision: {summary['decision']}")
        print(f"failures: {', '.join(failures) if failures else 'none'}")
        print("counts:")
        for name, count in summary["counts"].items():
            print(f"  {name}: {count}")
        print(f"untracked_runtime_count: {len(untracked_runtime)}")
        if untracked_runtime:
            print("untracked_runtime:")
            for path in untracked_runtime:
                print(f"  - {path}")
        print(f"secret_blockers: {len(secret_blockers)}")
        for finding in secret_blockers:
            print(f"  - {finding['path']}:{finding['line']} {finding['pattern']}")
        print(f"secret_warnings: {len(secret_warnings)}")
        for finding in secret_warnings:
            print(f"  - {finding['path']}:{finding['line']} {finding['pattern']}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
