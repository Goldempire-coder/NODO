do $$
begin
    if exists (
        select 1
        from disputes
        where reason = 'payment_not_received_or_incomplete'
    ) then
        raise exception 'cannot restore legacy disputes_reason_check while payment problem disputes exist';
    end if;
end
$$;

alter table disputes
    drop constraint if exists disputes_reason_check;

alter table disputes
    add constraint disputes_reason_check check (
        reason in (
            'business_no_payment_confirmation',
            'business_confirmed_payment_but_not_delivered',
            'payment_mobile_not_received',
            'amount_incorrect',
            'wrong_receiver_data',
            'other'
        )
    );
