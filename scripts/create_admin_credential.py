from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.core.config import load_settings  # noqa: E402
from app.modules.users.admin_passwords import hash_admin_password, normalize_admin_username  # noqa: E402
from app.modules.users.repository import PostgresUserRepository  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a NODO admin credential without writing the password to disk.")
    parser.add_argument("--username", required=True, help="Admin username, usually an email.")
    parser.add_argument("--role", choices=["support", "admin", "super_admin"], default="super_admin")
    parser.add_argument("--first-name", default="NODO Admin")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    username = normalize_admin_username(args.username)
    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm admin password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 2
    settings = load_settings(os.environ)
    repository = PostgresUserRepository(settings.database_url)
    user = repository.create_admin_user_with_credentials(
        username=username,
        password_hash=hash_admin_password(password),
        role=args.role,
        first_name=args.first_name,
    )
    print(f"Created admin credential for {username} with role {user.role} and user_id {user.id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
