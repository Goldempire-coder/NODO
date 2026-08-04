create table if not exists business_public_reputation_snapshots (
    business_id uuid primary key references businesses(id) on delete restrict,
    rating_avg numeric(3, 2) not null,
    ratings_count integer not null,
    reputation_tier text not null,
    source_calculated_at timestamptz not null,
    published_at timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint business_public_reputation_snapshots_rating_avg_check
        check (rating_avg >= 1.00 and rating_avg <= 5.00),
    constraint business_public_reputation_snapshots_ratings_count_check
        check (ratings_count >= 5),
    constraint business_public_reputation_snapshots_tier_check
        check (reputation_tier in ('new', 'active', 'reliable', 'elite'))
);

create index if not exists business_public_reputation_snapshots_published_at_idx
    on business_public_reputation_snapshots (published_at asc, business_id asc);
