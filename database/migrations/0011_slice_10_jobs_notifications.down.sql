drop index if exists businesses_founder_status_expires_at_idx;
drop index if exists ads_status_expires_at_idx;
drop index if exists orders_delivered_auto_complete_idx;
drop index if exists orders_payment_confirmed_delivery_deadline_idx;
drop index if exists orders_payment_confirmed_delivery_warning_idx;
drop index if exists orders_waiting_payment_deadline_idx;
drop index if exists job_runs_lock_key_idx;
drop index if exists job_runs_job_type_status_created_idx;
drop index if exists job_runs_job_type_started_at_idx;
drop index if exists notification_jobs_dispute_type_created_idx;
drop index if exists notification_jobs_business_type_created_idx;
drop index if exists notification_jobs_order_type_created_idx;
drop index if exists notification_jobs_type_status_scheduled_idx;
drop index if exists notification_jobs_status_scheduled_idx;
drop index if exists notification_jobs_dedupe_key_unique_idx;

alter table notification_jobs drop constraint if exists notification_jobs_terminal_timestamp_check;
alter table notification_jobs drop constraint if exists notification_jobs_type_check;

drop table if exists notification_jobs;

alter table job_runs drop constraint if exists job_runs_failed_error_check;
alter table job_runs drop constraint if exists job_runs_terminal_finished_at_check;
alter table job_runs drop constraint if exists job_runs_counters_non_negative_check;
alter table job_runs drop constraint if exists job_runs_attempts_non_negative_check;
alter table job_runs drop constraint if exists job_runs_duration_non_negative_check;
alter table job_runs drop constraint if exists job_runs_job_type_check;
alter table job_runs drop constraint if exists job_runs_status_check;

alter table job_runs drop column if exists failed_count;
alter table job_runs drop column if exists skipped_count;
alter table job_runs drop column if exists changed_count;
alter table job_runs drop column if exists processed_count;
alter table job_runs drop column if exists lock_acquired;
alter table job_runs drop column if exists duration_ms;
