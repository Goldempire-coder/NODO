alter table users add column if not exists terms_accepted_at timestamptz null;
alter table users add column if not exists terms_version text null;

