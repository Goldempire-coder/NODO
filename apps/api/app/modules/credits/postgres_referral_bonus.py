from __future__ import annotations

from app.core.errors import ApiError
from app.modules.credits.models import ReferralApprovalResult
from app.modules.credits.referral_codes import normalize_referral_code
from app.modules.credits.postgres_referrals import referral_event_from_row


def award_referral_on_business_approval_pg(
    connect,
    *,
    referred_business_id: str,
    referral_code: str | None,
    actor_user_id: str | None,
) -> ReferralApprovalResult:  # type: ignore[no-untyped-def]
    with connect() as conn:
        referred = conn.execute(
            "select id, verification_status from businesses where id = %s for update",
            (referred_business_id,),
        ).fetchone()
        if referred is None:
            conn.rollback()
            raise ApiError("REFERRAL_NOT_ALLOWED", status_code=409)
        business_approved = referred["verification_status"] != "approved"
        if business_approved:
            conn.execute(
                "update businesses set verification_status = 'approved', approved_at = now(), updated_at = now() where id = %s",
                (referred_business_id,),
            )

        existing = conn.execute(
            "select * from referral_events where referred_business_id = %s order by created_at asc, id asc limit 1 for update",
            (referred_business_id,),
        ).fetchone()
        if existing is not None:
            if existing["status"] != "pending":
                return ReferralApprovalResult(
                    event=referral_event_from_row(existing),
                    outcome="already_processed",
                    created=False,
                    business_approved=business_approved,
                )
            if str(existing["referrer_business_id"]) == referred_business_id:
                event = conn.execute(
                    """
                    update referral_events
                    set status = 'rejected', reject_reason = 'self_referral', rejected_at = now()
                    where id = %s returning *
                    """,
                    (existing["id"],),
                ).fetchone()
                conn.commit()
                return ReferralApprovalResult(
                    event=referral_event_from_row(event),
                    outcome="self_referral",
                    created=False,
                    business_approved=business_approved,
                    event_changed=True,
                )
            event = existing
            referrer_business_id = str(existing["referrer_business_id"])
            created = False
        else:
            normalized = normalize_referral_code(referral_code)
            if normalized is None:
                return ReferralApprovalResult(
                    event=None,
                    outcome="no_code",
                    created=False,
                    business_approved=business_approved,
                )

            code = conn.execute(
                "select * from referral_codes where code = %s and status = 'active'",
                (normalized,),
            ).fetchone()
            if code is None:
                return ReferralApprovalResult(
                    event=None,
                    outcome="invalid_code",
                    created=False,
                    business_approved=business_approved,
                )
            if str(code["business_id"]) == referred_business_id:
                return ReferralApprovalResult(
                    event=None,
                    outcome="self_referral",
                    created=False,
                    business_approved=business_approved,
                )

            referrer_business_id = str(code["business_id"])
            event = conn.execute(
                """
                insert into referral_events (
                    referral_code_id, referrer_business_id, referred_business_id,
                    status, credits_awarded, created_at
                )
                values (%s, %s, %s, 'pending', 0, now()) returning *
                """,
                (code["id"], code["business_id"], referred_business_id),
            ).fetchone()
            created = True

        referrer = conn.execute(
            "select * from businesses where id = %s for update",
            (referrer_business_id,),
        ).fetchone()
        remaining = max(0, 20 - (referrer["referral_credits_earned"] if referrer is not None else 20))
        award = min(5, remaining)
        if referrer is None or award == 0:
            event = conn.execute(
                """
                update referral_events
                set status = 'rejected', reject_reason = 'referral_cap_reached', rejected_at = now()
                where id = %s returning *
                """,
                (event["id"],),
            ).fetchone()
            conn.commit()
            return ReferralApprovalResult(
                event=referral_event_from_row(event),
                outcome="cap_reached",
                created=created,
                business_approved=business_approved,
                event_changed=True,
            )

        wallet = _referrer_wallet_for_update(conn, referrer_business_id)
        available_after = wallet["available_credits"] + award
        conn.execute(
            """
            update credit_wallets
            set available_credits = %s,
                lifetime_bonus_credits = lifetime_bonus_credits + %s,
                updated_at = now()
            where business_id = %s
            """,
            (available_after, award, referrer_business_id),
        )
        conn.execute(
            """
            update businesses
            set referral_credits_earned = referral_credits_earned + %s, updated_at = now()
            where id = %s
            """,
            (award, referrer_business_id),
        )
        event = conn.execute(
            """
            update referral_events
            set status = 'rewarded', credits_awarded = %s,
                approved_at = now(), rewarded_at = now()
            where id = %s returning *
            """,
            (award, event["id"]),
        ).fetchone()
        conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_referral_id, reason, source, reference_type, reference_id,
                created_by, created_at
            )
            values (%s, 'referral_bonus', %s, %s, %s, %s, %s, %s, %s,
                %s, 'referral_bonus_business_approval', 'referral_events',
                'referral_event', %s, %s, now())
            """,
            (
                referrer_business_id,
                award,
                wallet["available_credits"],
                available_after,
                wallet["blocked_credits"],
                wallet["blocked_credits"],
                wallet["consumed_credits"],
                wallet["consumed_credits"],
                event["id"],
                event["id"],
                actor_user_id,
            ),
        )
        conn.commit()
    return ReferralApprovalResult(
        event=referral_event_from_row(event),
        outcome="rewarded",
        created=created,
        business_approved=business_approved,
        event_changed=True,
    )


def _referrer_wallet_for_update(conn, business_id: str):  # type: ignore[no-untyped-def]
    wallet = conn.execute(
        "select * from credit_wallets where business_id = %s for update",
        (business_id,),
    ).fetchone()
    if wallet is not None:
        return wallet
    return conn.execute(
        """
        insert into credit_wallets (
            business_id, available_credits, blocked_credits, consumed_credits, created_at, updated_at
        ) values (%s, 0, 0, 0, now(), now()) returning *
        """,
        (business_id,),
    ).fetchone()
