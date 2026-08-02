alter table payment_reports
    drop constraint if exists payment_reports_zelle_required_check;

alter table payment_reports
    add constraint payment_reports_zelle_required_check check (
        payment_type <> 'zelle'
        or (
            (
                proof_file_id is null
                and proof_content_sha256 is null
            )
            or (
                proof_file_id is not null
                and proof_content_sha256 is not null
            )
        )
    );
