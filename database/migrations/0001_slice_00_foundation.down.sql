drop table if exists app_metadata;
drop trigger if exists audit_logs_prevent_delete on audit_logs;
drop trigger if exists audit_logs_prevent_update on audit_logs;
drop function if exists prevent_audit_logs_mutation();
drop table if exists audit_logs;
drop table if exists job_runs;
drop table if exists users;
