do $$
begin
    if exists (
        select 1
        from payment_reports
        where tx_hash is not null
          and lower(trim(tx_hash)) !~ '^(0x)?[a-f0-9]{64}$'
    ) then
        raise exception using
            errcode = '23514',
            message = 'invalid payment report transaction hashes require review';
    end if;

    if exists (
        select 1
        from payment_reports
        where tx_hash is not null
        group by
            coalesce(upper(trim(network)), ''),
            regexp_replace(lower(trim(tx_hash)), '^0x', '')
        having count(*) > 1
    ) then
        raise exception using
            errcode = '23505',
            message = 'duplicate canonical payment report transaction hashes require review';
    end if;
end
$$;

update payment_reports
set tx_hash = regexp_replace(lower(trim(tx_hash)), '^0x', '')
where tx_hash is not null;

create unique index if not exists payment_reports_network_tx_hash_unique_idx
    on payment_reports (
        coalesce(upper(trim(network)), ''),
        regexp_replace(lower(trim(tx_hash)), '^0x', '')
    )
    where tx_hash is not null;

alter table payment_reports drop constraint if exists payment_reports_tx_hash_format_check;
alter table payment_reports
    add constraint payment_reports_tx_hash_format_check check (
        tx_hash is null
        or tx_hash ~ '^[a-f0-9]{64}$'
    );

do $$
begin
    if exists (
        select 1
        from payment_reports
        where proof_file_id is not null
        group by proof_file_id
        having count(*) > 1
    ) then
        raise exception using
            errcode = '23505',
            message = 'duplicate payment report proof files require review';
    end if;
end
$$;

create unique index if not exists payment_reports_proof_file_unique_idx
    on payment_reports (proof_file_id)
    where proof_file_id is not null;

alter table payment_reports add column if not exists proof_content_sha256 text null;

update payment_reports
set proof_content_sha256 = file_assets.metadata_json ->> 'content_sha256'
from file_assets
where payment_reports.proof_file_id = file_assets.id
  and payment_reports.proof_content_sha256 is null
  and file_assets.metadata_json ? 'content_sha256';

do $$
begin
    if exists (
        select 1
        from payment_reports
        where proof_file_id is not null
          and proof_content_sha256 is null
    ) then
        raise exception using
            errcode = '23514',
              message = 'payment reports with proof files missing content hashes require controlled backfill';
    end if;

    if exists (
        select 1
        from payment_reports
        where proof_content_sha256 is not null
          and proof_content_sha256 !~ '^[a-f0-9]{64}$'
    ) then
        raise exception using
            errcode = '23514',
            message = 'invalid payment report proof content hashes require review';
    end if;

    if exists (
        select 1
        from payment_reports
        where proof_content_sha256 is not null
        group by proof_content_sha256
        having count(*) > 1
    ) then
        raise exception using
            errcode = '23505',
            message = 'duplicate payment report proof content hashes require review';
    end if;
end
$$;

create unique index if not exists payment_reports_proof_content_sha256_unique_idx
    on payment_reports (proof_content_sha256)
    where proof_content_sha256 is not null;

alter table payment_reports drop constraint if exists payment_reports_proof_content_sha256_check;
alter table payment_reports
    add constraint payment_reports_proof_content_sha256_check check (
        proof_content_sha256 is null
        or proof_content_sha256 ~ '^[a-f0-9]{64}$'
    );

alter table orders drop constraint if exists orders_cancel_reason_check;
alter table orders
    add constraint orders_cancel_reason_check check (
        cancel_reason is null
        or cancel_reason in (
            'remitter_cancelled_before_payment',
            'payment_not_reported_in_time',
            'business_unavailable',
            'admin_cancelled'
        )
    );

alter table notification_jobs drop constraint if exists notification_jobs_type_check;
alter table notification_jobs
    add constraint notification_jobs_type_check check (
        notification_type in (
            'order_payment_deadline_warning',
            'order_cancelled_payment_not_reported',
            'order_business_response_warning',
            'order_disputed_business_no_payment_confirmation',
            'order_delivery_warning',
            'order_disputed_business_confirmed_payment_but_not_delivered',
            'delivered_reminder_immediate',
            'delivered_reminder_12h',
            'delivered_reminder_23h',
            'order_auto_completed_after_24h',
            'ad_expired',
            'founder_access_expired',
            'order_created_business',
            'payment_reported_business',
            'payment_confirmed_client',
            'payment_rejected_client',
            'order_delivered_client',
            'order_disputed_parties_admin',
            'order_cancelled_business_unavailable',
            'business_suspended_owner',
            'business_reactivated_owner',
            'business_blocked_owner',
            'user_suspended_account',
            'user_reactivated_account',
            'user_blocked_account',
            'business_access_suspended_owner',
            'business_access_reactivated_owner',
            'business_access_blocked_owner',
            'business_access_revoked_owner',
            'support_ticket_resolved_participant',
            'support_ticket_closed_participant',
            'order_message_created_business',
            'order_message_created_client',
            'support_message_created_participant'
        )
    );
