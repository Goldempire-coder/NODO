from __future__ import annotations

import argparse
from pathlib import Path

import psycopg
import redis

from local_hardening_common import DEFAULT_ENV_FILE, add_api_path, configure_env, write_json

add_api_path()
from app.shared.db.connection import connect  # noqa: E402

REQUIRED_TABLES = {
    "users",
    "sessions",
    "audit_logs",
    "job_runs",
    "app_metadata",
    "businesses",
    "business_verification_submissions",
    "business_access_links",
    "business_payment_methods",
    "file_assets",
    "ads",
    "credit_wallets",
    "credits_ledger",
    "orders",
    "order_state_events",
    "payment_reports",
    "messages",
    "message_attachments",
    "disputes",
    "dispute_events",
    "credit_purchases",
    "referral_codes",
    "referral_events",
    "notification_jobs",
    "business_intake_requests",
}

REQUIRED_INDEX_FRAGMENTS = {
    "users_telegram_id_unique",
    "audit_logs_resource_created_at_idx",
    "sessions_refresh_token_hash",
    "businesses_one_active_per_owner_idx",
    "ads_marketplace_active_idx",
    "orders_public_order_code",
    "orders_remitter_idempotency_idx",
    "payment_reports_reported_by_idempotency_idx",
    "messages_order_created_idx",
    "disputes_status_created_idx",
    "credit_purchases_stripe_event_idx",
    "notification_jobs_dedupe_key_unique_idx",
    "business_access_links_active_business_user_idx",
}

REQUIRED_COLUMNS = {
    "users": {"terms_accepted_at", "terms_version", "phone", "role", "status"},
    "business_access_links": {
        "business_id",
        "user_id",
        "telegram_id_snapshot",
        "role_in_business",
        "status",
    },
    "business_intake_requests": {
        "telegram_user_id",
        "telegram_chat_id",
        "contact_phone",
        "business_phone",
        "last_step",
        "last_update_id",
        "status",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--output", default="evidence/slice_runs/slice_11_local_schema_validation.json")
    args = parser.parse_args()

    env = configure_env(Path(args.env_file))
    failures: list[str] = []
    with connect(env["DATABASE_URL"], row_factory=psycopg.rows.dict_row) as conn:
        table_rows = conn.execute(
            "select table_name from information_schema.tables where table_schema = 'public'"
        ).fetchall()
        tables = {row["table_name"] for row in table_rows}
        missing_tables = sorted(REQUIRED_TABLES - tables)
        failures.extend(f"missing_table:{table}" for table in missing_tables)

        index_rows = conn.execute(
            "select indexname from pg_indexes where schemaname = 'public'"
        ).fetchall()
        indexes = {row["indexname"] for row in index_rows}
        missing_indexes = sorted(fragment for fragment in REQUIRED_INDEX_FRAGMENTS if not any(fragment in index for index in indexes))
        failures.extend(f"missing_index:{index}" for index in missing_indexes)

        column_rows = conn.execute(
            """
            select table_name, column_name
            from information_schema.columns
            where table_schema = 'public'
            """
        ).fetchall()
        columns_by_table: dict[str, set[str]] = {}
        for row in column_rows:
            columns_by_table.setdefault(row["table_name"], set()).add(row["column_name"])
        for table, required_columns in REQUIRED_COLUMNS.items():
            present = columns_by_table.get(table, set())
            for column in sorted(required_columns - present):
                failures.append(f"missing_column:{table}.{column}")

        order_statuses = conn.execute(
            """
            select constraint_name, check_clause
            from information_schema.check_constraints
            where check_clause like '%payment_reported%' or check_clause like '%delivered%'
            """
        ).fetchall()
        if not order_statuses:
            failures.append("missing_order_status_checks")

    redis_client = redis.Redis.from_url(env["REDIS_URL"], socket_connect_timeout=3, socket_timeout=3)
    redis_ping = redis_client.ping()
    payload = {
        "slice": "slice_11_hardening_deploy",
        "phase": "local_schema_validation",
        "table_count": len(tables),
        "index_count": len(indexes),
        "required_tables": sorted(REQUIRED_TABLES),
        "redis_ping": bool(redis_ping),
        "failures": failures,
        "exit_code": 1 if failures else 0,
    }
    write_json(Path(args.output), payload)
    print(payload)
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
