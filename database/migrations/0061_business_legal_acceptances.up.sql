create table if not exists business_legal_acceptances (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id) on delete cascade,
    user_id uuid not null references users(id) on delete restrict,
    document_set text not null,
    document_version text not null,
    confirmation text not null,
    surface text not null,
    locale text not null default 'es',
    request_id text not null,
    accepted_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    constraint business_legal_acceptances_document_set_check
        check (document_set in ('business_terms', 'business_credit_terms')),
    constraint business_legal_acceptances_confirmation_check
        check (confirmation = 'ACCEPTED_BY_AUTHORIZED_BUSINESS_REPRESENTATIVE')
);

create unique index if not exists business_legal_acceptances_document_uidx
    on business_legal_acceptances (business_id, user_id, document_set, document_version);

create index if not exists business_legal_acceptances_business_idx
    on business_legal_acceptances (business_id, document_set, accepted_at desc);
