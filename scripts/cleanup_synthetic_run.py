from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import psycopg

from local_hardening_common import DEFAULT_ENV_FILE, add_api_path, configure_env, write_json

add_api_path()
from app.shared.db.connection import connect  # noqa: E402


RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{12,120}$")


COUNT_TABLES = [
    "users",
    "sessions",
    "businesses",
    "business_verification_submissions",
    "business_access_links",
    "business_payment_methods",
    "credit_wallets",
    "ads",
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
    "file_assets",
]


DELETE_STEPS = [
    ("notification_jobs", "delete from notification_jobs where id in (select id from cleanup_notification_jobs)"),
    ("dispute_events", "delete from dispute_events where id in (select id from cleanup_dispute_events)"),
    ("disputes", "delete from disputes where id in (select id from cleanup_disputes)"),
    ("message_attachments", "delete from message_attachments where id in (select id from cleanup_message_attachments)"),
    ("messages", "delete from messages where id in (select id from cleanup_messages)"),
    ("payment_reports", "delete from payment_reports where id in (select id from cleanup_payment_reports)"),
    ("order_state_events", "delete from order_state_events where id in (select id from cleanup_order_state_events)"),
    ("referral_events", "delete from referral_events where id in (select id from cleanup_referral_events)"),
    ("referral_codes", "delete from referral_codes where id in (select id from cleanup_referral_codes)"),
    ("business_intake_requests", "delete from business_intake_requests where id in (select id from cleanup_business_intake_requests)"),
    (
        "business_verification_submissions",
        "delete from business_verification_submissions where id in (select id from cleanup_business_verification_submissions)",
    ),
    ("business_access_links", "delete from business_access_links where id in (select id from cleanup_business_access_links)"),
    (
        "ads_credit_ledger_refs",
        """
        update ads
        set credit_hold_ledger_id = null,
            credit_consumed_ledger_id = null,
            updated_at = now()
        where id in (select id from cleanup_ads)
           or credit_hold_ledger_id in (select id from cleanup_credits_ledger)
           or credit_consumed_ledger_id in (select id from cleanup_credits_ledger)
        """,
    ),
    ("credits_ledger", "delete from credits_ledger where id in (select id from cleanup_credits_ledger)"),
    ("orders", "delete from orders where id in (select id from cleanup_orders)"),
    ("credit_purchases", "delete from credit_purchases where id in (select id from cleanup_credit_purchases)"),
    ("ads", "delete from ads where id in (select id from cleanup_ads)"),
    ("business_payment_methods", "delete from business_payment_methods where id in (select id from cleanup_business_payment_methods)"),
    ("credit_wallets", "delete from credit_wallets where id in (select id from cleanup_credit_wallets)"),
    ("file_assets", "delete from file_assets where id in (select id from cleanup_file_assets)"),
    ("businesses", "delete from businesses where id in (select id from cleanup_businesses)"),
    ("sessions", "delete from sessions where id in (select id from cleanup_sessions)"),
]


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be 12-120 chars and contain only letters, numbers, _, ., :, or -")
    if "%" in run_id or "_" * len(run_id) == run_id:
        raise ValueError("run_id contains unsafe wildcard-like content")


def scalar(conn: psycopg.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def create_id_table(conn: psycopg.Connection, name: str, sql: str, params: tuple[Any, ...] = ()) -> None:
    conn.execute(f"drop table if exists {name}")
    conn.execute(f"create temp table {name} as {sql}", params)
    conn.execute(f"create unique index {name}_id_idx on {name}(id)")


def populate_cleanup_tables(conn: psycopg.Connection, run_id: str) -> None:
    like = f"%{run_id}%"
    prefix = f"{run_id}%"

    create_id_table(
        conn,
        "cleanup_users",
        """
        select id
        from users
        where username ilike %s
           or first_name ilike %s
        """,
        (like, like),
    )
    create_id_table(
        conn,
        "cleanup_businesses",
        """
        select id
        from businesses
        where business_name ilike %s
           or owner_user_id in (select id from cleanup_users)
        """,
        (like,),
    )
    create_id_table(
        conn,
        "cleanup_ads",
        """
        select id
        from ads
        where business_id in (select id from cleanup_businesses)
        """,
    )
    create_id_table(
        conn,
        "cleanup_orders",
        """
        select id
        from orders
        where business_id in (select id from cleanup_businesses)
           or remitter_user_id in (select id from cleanup_users)
           or ad_id in (select id from cleanup_ads)
           or idempotency_key ilike %s
        """,
        (prefix,),
    )
    conn.execute(
        """
        insert into cleanup_ads(id)
        select distinct ad_id
        from orders
        where id in (select id from cleanup_orders)
        on conflict do nothing
        """
    )
    create_id_table(
        conn,
        "cleanup_disputes",
        """
        select id
        from disputes
        where order_id in (select id from cleanup_orders)
           or opened_by_user_id in (select id from cleanup_users)
           or resolved_by_admin_id in (select id from cleanup_users)
        """,
    )
    create_id_table(
        conn,
        "cleanup_messages",
        """
        select id
        from messages
        where order_id in (select id from cleanup_orders)
           or sender_user_id in (select id from cleanup_users)
           or idempotency_key ilike %s
        """,
        (prefix,),
    )
    create_id_table(
        conn,
        "cleanup_message_attachments",
        """
        select id
        from message_attachments
        where order_id in (select id from cleanup_orders)
           or message_id in (select id from cleanup_messages)
           or uploaded_by_user_id in (select id from cleanup_users)
        """,
    )
    create_id_table(
        conn,
        "cleanup_payment_reports",
        """
        select id
        from payment_reports
        where order_id in (select id from cleanup_orders)
           or reported_by_user_id in (select id from cleanup_users)
           or idempotency_key ilike %s
        """,
        (prefix,),
    )
    create_id_table(
        conn,
        "cleanup_credit_purchases",
        """
        select id
        from credit_purchases
        where business_id in (select id from cleanup_businesses)
           or idempotency_key ilike %s
           or stripe_checkout_session_id ilike %s
           or stripe_event_id ilike %s
           or manual_payment_reference ilike %s
        """,
        (prefix, like, like, like),
    )
    create_id_table(
        conn,
        "cleanup_referral_codes",
        """
        select id
        from referral_codes
        where business_id in (select id from cleanup_businesses)
        """,
    )
    create_id_table(
        conn,
        "cleanup_referral_events",
        """
        select id
        from referral_events
        where referrer_business_id in (select id from cleanup_businesses)
           or referred_business_id in (select id from cleanup_businesses)
           or referral_code_id in (select id from cleanup_referral_codes)
           or related_credit_purchase_id in (select id from cleanup_credit_purchases)
        """,
    )
    create_id_table(
        conn,
        "cleanup_notification_jobs",
        """
        select id
        from notification_jobs
        where recipient_user_id in (select id from cleanup_users)
           or order_id in (select id from cleanup_orders)
           or business_id in (select id from cleanup_businesses)
           or dispute_id in (select id from cleanup_disputes)
           or dedupe_key ilike %s
        """,
        (like,),
    )
    create_id_table(
        conn,
        "cleanup_business_intake_requests",
        """
        select id
        from business_intake_requests
        where business_name ilike %s
           or referral_code ilike %s
           or contact_phone ilike %s
           or created_business_id in (select id from cleanup_businesses)
           or linked_telegram_user_id in (select telegram_id from users where id in (select id from cleanup_users))
        """,
        (like, like, like),
    )
    create_id_table(
        conn,
        "cleanup_order_state_events",
        """
        select id
        from order_state_events
        where order_id in (select id from cleanup_orders)
           or actor_user_id in (select id from cleanup_users)
           or request_id ilike %s
        """,
        (prefix,),
    )
    create_id_table(
        conn,
        "cleanup_dispute_events",
        """
        select id
        from dispute_events
        where dispute_id in (select id from cleanup_disputes)
           or order_id in (select id from cleanup_orders)
           or actor_user_id in (select id from cleanup_users)
        """,
    )
    create_id_table(
        conn,
        "cleanup_business_verification_submissions",
        """
        select id
        from business_verification_submissions
        where business_id in (select id from cleanup_businesses)
           or submitted_by_user_id in (select id from cleanup_users)
           or admin_reviewed_by_user_id in (select id from cleanup_users)
        """,
    )
    create_id_table(
        conn,
        "cleanup_business_access_links",
        """
        select id
        from business_access_links
        where business_id in (select id from cleanup_businesses)
           or user_id in (select id from cleanup_users)
           or linked_by_admin_id in (select id from cleanup_users)
        """,
    )
    create_id_table(
        conn,
        "cleanup_business_payment_methods",
        """
        select id
        from business_payment_methods
        where business_id in (select id from cleanup_businesses)
           or account_value ilike %s
        """,
        (like,),
    )
    conn.execute(
        """
        insert into cleanup_ads(id)
        select distinct id
        from ads
        where payment_method_id in (select id from cleanup_business_payment_methods)
        on conflict do nothing
        """
    )
    create_id_table(
        conn,
        "cleanup_credit_wallets",
        """
        select id
        from credit_wallets
        where business_id in (select id from cleanup_businesses)
        """,
    )
    create_id_table(
        conn,
        "cleanup_credits_ledger",
        """
        select id
        from credits_ledger
        where business_id in (select id from cleanup_businesses)
           or related_ad_id in (select id from cleanup_ads)
           or related_order_id in (select id from cleanup_orders)
           or related_credit_purchase_id in (select id from cleanup_credit_purchases)
           or created_by in (select id from cleanup_users)
        """,
    )
    conn.execute(
        """
        insert into cleanup_ads(id)
        select distinct id
        from ads
        where credit_hold_ledger_id in (select id from cleanup_credits_ledger)
           or credit_consumed_ledger_id in (select id from cleanup_credits_ledger)
        on conflict do nothing
        """
    )
    create_id_table(
        conn,
        "cleanup_file_assets",
        """
        select id
        from file_assets
        where owner_user_id in (select id from cleanup_users)
           or storage_path ilike %s
           or (resource_type = 'business' and resource_id in (select id from cleanup_businesses))
           or (resource_type = 'payment_report' and resource_id in (select id from cleanup_orders))
           or (resource_type = 'message' and resource_id in (select id from cleanup_messages))
           or (resource_type = 'credit_purchase' and resource_id in (select id from cleanup_credit_purchases))
           or (resource_type = 'business_intake' and resource_id in (select id from cleanup_business_intake_requests))
        """,
        (like,),
    )
    create_id_table(
        conn,
        "cleanup_sessions",
        """
        select id
        from sessions
        where user_id in (select id from cleanup_users)
        """,
    )


def collect_counts(conn: psycopg.Connection, *, run_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in COUNT_TABLES:
        counts[table] = scalar(conn, f"select count(*) from cleanup_{table}")
    counts["audit_logs_retained"] = scalar(
        conn,
        """
        select count(*)
        from audit_logs
        where request_id ilike %s
           or actor_user_id in (select id from cleanup_users)
           or resource_id in (
               select id from cleanup_businesses
               union select id from cleanup_ads
               union select id from cleanup_orders
               union select id from cleanup_disputes
               union select id from cleanup_credit_purchases
               union select id from cleanup_business_intake_requests
           )
        """,
        (f"%{run_id}%",),
    )
    return counts


def execute_deletes(conn: psycopg.Connection) -> dict[str, int]:
    deleted: dict[str, int] = {}
    for label, sql in DELETE_STEPS:
        result = conn.execute(sql)
        deleted[label] = result.rowcount if result.rowcount is not None else 0
    return deleted


def cleanup(*, env_file: Path, run_id: str, execute: bool) -> dict[str, Any]:
    validate_run_id(run_id)
    env = configure_env(env_file)
    db_url = env["DATABASE_URL"]
    with connect(db_url) as conn:
        populate_cleanup_tables(conn, run_id)
        counts = collect_counts(conn, run_id=run_id)
        deleted = execute_deletes(conn) if execute else {}
        if execute:
            conn.commit()
        else:
            conn.rollback()
    return {
        "run_id": run_id,
        "mode": "execute" if execute else "dry_run",
        "matched_counts": counts,
        "deleted_counts": deleted,
        "users_deleted": 0,
        "audit_logs_deleted": 0,
        "retained_by_design": {
            "users": "Synthetic users are retained because audit_logs has append-only triggers and actor_user_id references users.",
            "audit_logs": "Audit logs are append-only evidence and are not deleted by this cleanup.",
        },
        "exit_code": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    payload = cleanup(env_file=Path(args.env_file), run_id=args.run_id, execute=args.execute)
    if args.output:
        write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
