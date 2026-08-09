alter table businesses
    add column if not exists ad_publication_paused_until timestamptz null;

comment on column businesses.ad_publication_paused_until is
    'Internal publication pause boundary; active while database now is earlier than this value.';
