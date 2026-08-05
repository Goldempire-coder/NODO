do $$
begin
    if exists (
        select 1
        from order_receiver_details
        where phone !~ '^\+58[0-9]{10}$'
    ) then
        raise exception using
            errcode = '23514',
            message = '0048 rollback preflight failed: local receiver phone rows require preservation';
    end if;
end
$$;

alter table order_receiver_details
    drop constraint if exists order_receiver_details_phone_check;

alter table order_receiver_details
    add constraint order_receiver_details_phone_check
    check (phone ~ '^\+58[0-9]{10}$') not valid;

alter table order_receiver_details
    validate constraint order_receiver_details_phone_check;
