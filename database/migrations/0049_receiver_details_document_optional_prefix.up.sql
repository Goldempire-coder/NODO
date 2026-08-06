do $$
begin
    if exists (
        select 1
        from order_receiver_details
        where document !~ '^([VEJGP])?[0-9]{6,10}$'
    ) then
        raise exception using
            errcode = '23514',
            message = '0049 preflight failed: incompatible receiver document rows exist';
    end if;
end
$$;

alter table order_receiver_details
    drop constraint if exists order_receiver_details_document_check;

alter table order_receiver_details
    add constraint order_receiver_details_document_check
    check (document ~ '^([VEJGP])?[0-9]{6,10}$') not valid;

alter table order_receiver_details
    validate constraint order_receiver_details_document_check;
