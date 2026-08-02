do $$
begin
    if exists (
        select 1
        from payment_reports
        where payment_type = 'zelle'
          and (
              proof_file_id is null
              or proof_content_sha256 is null
          )
    ) then
        raise exception using
            errcode = '23514',
            message = 'zelle payment reports without proof require review before rollback';
    end if;
end
$$;

alter table payment_reports
    drop constraint if exists payment_reports_zelle_required_check;

alter table payment_reports
    add constraint payment_reports_zelle_required_check check (
        payment_type <> 'zelle'
        or (
            proof_file_id is not null
            and proof_content_sha256 is not null
        )
    );
