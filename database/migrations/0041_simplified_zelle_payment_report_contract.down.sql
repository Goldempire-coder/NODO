do $$
begin
    if exists (
        select 1
        from payment_reports
        where payment_type = 'zelle'
          and (
              payment_reference is null
              or payment_sender_name is null
          )
    ) then
        raise exception using
            errcode = '23514',
            message = 'payment reports without legacy Zelle sender fields require review';
    end if;
end
$$;

alter table payment_reports
    drop constraint if exists payment_reports_zelle_required_check;

alter table payment_reports
    add constraint payment_reports_zelle_required_check check (
        payment_type <> 'zelle'
        or (
            payment_reference is not null
            and payment_sender_name is not null
            and proof_file_id is not null
        )
    );
