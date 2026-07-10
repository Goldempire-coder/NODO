from __future__ import annotations


def grant_referral_bonus_if_eligible_pg(conn, *, referred_business_id: str, purchase_id: str, actor_user_id: str | None) -> None:  # type: ignore[no-untyped-def]
    referral = _pending_referral_for_update(conn, referred_business_id)
    if referral is None:
        return

    existing_bonus = _referral_bonus_exists(conn, purchase_id)
    referrer = _referrer_for_update(conn, referral)
    if existing_bonus is None and _can_reward_referrer(referrer):
        referrer_wallet = _referrer_wallet_for_update(conn, referral)
        _reward_referral(conn, referral, referrer_wallet, purchase_id=purchase_id, actor_user_id=actor_user_id)
    elif referrer is None or referrer["referral_credits_earned"] >= 20:
        _reject_referral_cap_reached(conn, referral)


def _pending_referral_for_update(conn, referred_business_id: str):  # type: ignore[no-untyped-def]
    return conn.execute(
        """
        select * from referral_events
        where referred_business_id = %s and status = 'pending'
        order by created_at asc
        limit 1
        for update
        """,
        (referred_business_id,),
    ).fetchone()


def _referral_bonus_exists(conn, purchase_id: str) -> bool:  # type: ignore[no-untyped-def]
    row = conn.execute(
        """
        select 1 from credits_ledger
        where type = 'referral_bonus' and related_credit_purchase_id = %s
        limit 1
        """,
        (purchase_id,),
    ).fetchone()
    return row is not None


def _referrer_for_update(conn, referral):  # type: ignore[no-untyped-def]
    return conn.execute(
        "select * from businesses where id = %s for update",
        (referral["referrer_business_id"],),
    ).fetchone()


def _can_reward_referrer(referrer) -> bool:  # type: ignore[no-untyped-def]
    return referrer is not None and referrer["referral_credits_earned"] < 20


def _referrer_wallet_for_update(conn, referral):  # type: ignore[no-untyped-def]
    referrer_wallet = conn.execute(
        "select * from credit_wallets where business_id = %s for update",
        (referral["referrer_business_id"],),
    ).fetchone()
    if referrer_wallet is not None:
        return referrer_wallet
    return conn.execute(
        """
        insert into credit_wallets (business_id, available_credits, blocked_credits, consumed_credits, created_at, updated_at)
        values (%s, 0, 0, 0, now(), now()) returning *
        """,
        (referral["referrer_business_id"],),
    ).fetchone()


def _reward_referral(conn, referral, referrer_wallet, *, purchase_id: str, actor_user_id: str | None) -> None:  # type: ignore[no-untyped-def]
    referrer_available_after = referrer_wallet["available_credits"] + 1
    _update_referrer_wallet(conn, referral, referrer_available_after)
    _increment_referrer_bonus_count(conn, referral)
    _mark_referral_rewarded(conn, referral, purchase_id)
    _insert_referral_bonus_ledger(conn, referral, referrer_wallet, referrer_available_after, purchase_id, actor_user_id)


def _update_referrer_wallet(conn, referral, referrer_available_after: int) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        update credit_wallets
        set available_credits = %s,
            lifetime_bonus_credits = lifetime_bonus_credits + 1,
            updated_at = now()
        where business_id = %s
        """,
        (referrer_available_after, referral["referrer_business_id"]),
    )


def _increment_referrer_bonus_count(conn, referral) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        "update businesses set referral_credits_earned = referral_credits_earned + 1, updated_at = now() where id = %s",
        (referral["referrer_business_id"],),
    )


def _mark_referral_rewarded(conn, referral, purchase_id: str) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        update referral_events
        set status = 'rewarded',
            related_credit_purchase_id = %s,
            credits_awarded = 1,
            approved_at = now(),
            rewarded_at = now()
        where id = %s
        """,
        (purchase_id, referral["id"]),
    )


def _insert_referral_bonus_ledger(conn, referral, referrer_wallet, referrer_available_after: int, purchase_id: str, actor_user_id: str | None) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        insert into credits_ledger (
            business_id, type, amount, available_before, available_after,
            blocked_before, blocked_after, consumed_before, consumed_after,
            related_referral_id, related_credit_purchase_id, reason, source,
            reference_type, reference_id, created_by, created_at
        )
        values (%s, 'referral_bonus', 1, %s, %s, %s, %s, %s, %s,
            %s, %s, 'referral_bonus_first_approved_purchase', 'referral_events',
            'referral_event', %s, %s, now())
        """,
        (
            referral["referrer_business_id"],
            referrer_wallet["available_credits"],
            referrer_available_after,
            referrer_wallet["blocked_credits"],
            referrer_wallet["blocked_credits"],
            referrer_wallet["consumed_credits"],
            referrer_wallet["consumed_credits"],
            referral["id"],
            purchase_id,
            referral["id"],
            actor_user_id,
        ),
    )


def _reject_referral_cap_reached(conn, referral) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        update referral_events
        set status = 'rejected',
            reject_reason = 'referral_cap_reached',
            rejected_at = now()
        where id = %s
        """,
        (referral["id"],),
    )
