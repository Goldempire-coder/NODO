from __future__ import annotations

from app.core.errors import ApiError
from app.modules.credits.models import ReferralCodeRecord, ReferralEventRecord
from app.modules.credits.referral_codes import normalize_referral_code


def referral_event_from_row(row) -> ReferralEventRecord:  # type: ignore[no-untyped-def]
    return ReferralEventRecord(
        id=str(row["id"]),
        referral_code_id=str(row["referral_code_id"]),
        referrer_business_id=str(row["referrer_business_id"]),
        referred_business_id=str(row["referred_business_id"]),
        related_credit_purchase_id=str(row["related_credit_purchase_id"]) if row["related_credit_purchase_id"] else None,
        status=row["status"],
        credits_awarded=row["credits_awarded"],
        reject_reason=row["reject_reason"],
        created_at=row["created_at"],
        approved_at=row["approved_at"],
        rewarded_at=row["rewarded_at"],
        rejected_at=row["rejected_at"],
    )


def get_or_create_referral_code_pg(connect, business_id: str) -> ReferralCodeRecord:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute("select * from referral_codes where business_id = %s", (business_id,)).fetchone()
        if row is None:
            row = conn.execute(
                """
                insert into referral_codes (business_id, code, status, created_at, updated_at)
                values (%s, %s, 'active', now(), now()) returning *
                """,
                (business_id, f"NODO{business_id.replace('-', '')[:8].upper()}"),
            ).fetchone()
            conn.execute("update businesses set referral_code = %s, updated_at = now() where id = %s", (row["code"], business_id))
            conn.commit()
    return ReferralCodeRecord(id=str(row["id"]), business_id=str(row["business_id"]), code=row["code"], status=row["status"], created_at=row["created_at"], updated_at=row["updated_at"], disabled_at=row["disabled_at"])


def apply_referral_code_pg(connect, *, referred_business_id: str, referral_code: str) -> ReferralEventRecord:  # type: ignore[no-untyped-def]
    normalized = normalize_referral_code(referral_code)
    with connect() as conn:
        conn.execute("select id from businesses where id = %s for update", (referred_business_id,)).fetchone()
        existing = conn.execute(
            "select 1 from referral_events where referred_business_id = %s limit 1",
            (referred_business_id,),
        ).fetchone()
        if existing:
            raise ApiError("REFERRAL_ALREADY_USED", status_code=409)
        code = conn.execute("select * from referral_codes where code = %s and status = 'active'", (normalized,)).fetchone()
        if code is None:
            raise ApiError("REFERRAL_CODE_NOT_FOUND", status_code=404)
        if str(code["business_id"]) == referred_business_id:
            raise ApiError("REFERRAL_NOT_ALLOWED", status_code=409)
        row = conn.execute(
            """
            insert into referral_events (
                referral_code_id, referrer_business_id, referred_business_id,
                status, credits_awarded, created_at
            )
            values (%s, %s, %s, 'pending', 0, now()) returning *
            """,
            (code["id"], code["business_id"], referred_business_id),
        ).fetchone()
        conn.commit()
    return referral_event_from_row(row)


def list_referral_events_for_business_pg(connect, business_id: str) -> list[ReferralEventRecord]:  # type: ignore[no-untyped-def]
    with connect() as conn:
        rows = conn.execute(
            """
            select * from referral_events
            where referrer_business_id = %s or referred_business_id = %s
            order by created_at desc
            """,
            (business_id, business_id),
        ).fetchall()
    return [referral_event_from_row(row) for row in rows]


def admin_referral_summary_pg(connect, business_id: str) -> dict:  # type: ignore[no-untyped-def]
    with connect() as conn:
        business = conn.execute(
            "select referral_credits_earned from businesses where id = %s",
            (business_id,),
        ).fetchone()
        incoming = conn.execute(
            """
            select e.*, c.code, b.business_name as referrer_business_name
            from referral_events e
            join referral_codes c on c.id = e.referral_code_id
            join businesses b on b.id = e.referrer_business_id
            where e.referred_business_id = %s
            order by e.created_at asc, e.id asc
            limit 1
            """,
            (business_id,),
        ).fetchone()
        outgoing = conn.execute(
            """
            select e.*, b.business_name as referred_business_name
            from referral_events e
            join businesses b on b.id = e.referred_business_id
            where e.referrer_business_id = %s
            order by e.created_at desc, e.id desc
            limit 51
            """,
            (business_id,),
        ).fetchall()
    earned = business["referral_credits_earned"] if business else 0
    outgoing_page = outgoing[:50]
    return {
        "referred_by": (
            {
                "business_id": str(incoming["referrer_business_id"]),
                "business_name": incoming["referrer_business_name"],
            }
            if incoming
            else None
        ),
        "code_used": incoming["code"] if incoming else None,
        "earned_credits": earned,
        "remaining_bonus_credits": max(0, 20 - earned),
        "cap": 20,
        "referred_businesses_truncated": len(outgoing) > 50,
        "referred_businesses": [
            {
                "business_id": str(row["referred_business_id"]),
                "business_name": row["referred_business_name"],
                "status": row["status"],
                "credits_awarded": row["credits_awarded"],
                "created_at": row["created_at"].isoformat(),
                "rewarded_at": row["rewarded_at"].isoformat() if row["rewarded_at"] else None,
            }
            for row in outgoing_page
        ],
    }
