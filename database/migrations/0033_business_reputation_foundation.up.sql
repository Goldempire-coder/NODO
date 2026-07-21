alter table businesses
    add column if not exists reputation_tier text not null default 'new',
    add column if not exists ratings_count integer not null default 0,
    add column if not exists business_failure_orders_count integer not null default 0,
    add column if not exists lost_disputes_count integer not null default 0,
    add column if not exists success_rate numeric(5,2) null,
    add column if not exists average_delivery_seconds integer null,
    add column if not exists reputation_calculated_at timestamptz null;

alter table businesses
    add constraint businesses_reputation_tier_check
        check (reputation_tier in ('new', 'active', 'reliable', 'elite')),
    add constraint businesses_reputation_aggregates_check
        check (
            ratings_count >= 0
            and business_failure_orders_count >= 0
            and lost_disputes_count >= 0
            and (rating_avg is null or rating_avg between 1.00 and 5.00)
            and (success_rate is null or success_rate between 0.00 and 100.00)
            and (average_delivery_seconds is null or average_delivery_seconds >= 0)
        );

create table if not exists ratings (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null,
    business_id uuid not null,
    rater_user_id uuid not null,
    stars smallint not null,
    created_at timestamptz not null default now(),
    constraint ratings_order_fk foreign key (order_id) references orders(id),
    constraint ratings_business_fk foreign key (business_id) references businesses(id),
    constraint ratings_rater_user_fk foreign key (rater_user_id) references users(id),
    constraint ratings_order_unique unique (order_id),
    constraint ratings_stars_check check (stars between 1 and 5)
);

create index if not exists businesses_reputation_tier_completed_idx
    on businesses (reputation_tier, completed_orders_count desc);

create index if not exists ratings_business_created_idx
    on ratings (business_id, created_at desc);

create index if not exists ratings_rater_created_idx
    on ratings (rater_user_id, created_at desc);
