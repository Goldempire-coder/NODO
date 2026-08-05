do $$
begin
    if exists (
        select 1
        from order_receiver_details
        where char_length(phone) not between 11 and 32
           or phone !~ '^[0-9+() -]+$'
           or regexp_replace(phone, '[ ()-]', '', 'g') !~
              '^(0(412|414|416|424|426)[0-9]{7}|[+]58(412|414|416|424|426)[0-9]{7})$'
    ) then
        raise exception using
            errcode = '23514',
            message = '0048 preflight failed: incompatible receiver phone rows exist';
    end if;
end
$$;

alter table order_receiver_details
    drop constraint if exists order_receiver_details_phone_check;

alter table order_receiver_details
    add constraint order_receiver_details_phone_check check (
        char_length(phone) between 11 and 32
        and phone ~ '^[0-9+() -]+$'
        and regexp_replace(phone, '[ ()-]', '', 'g') ~
            '^(0(412|414|416|424|426)[0-9]{7}|[+]58(412|414|416|424|426)[0-9]{7})$'
    ) not valid;

alter table order_receiver_details
    validate constraint order_receiver_details_phone_check;
