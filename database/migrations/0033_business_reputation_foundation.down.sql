drop index if exists ratings_rater_created_idx;
drop index if exists ratings_business_created_idx;
drop index if exists businesses_reputation_tier_completed_idx;

drop table if exists ratings;

alter table businesses
    drop constraint if exists businesses_reputation_aggregates_check,
    drop constraint if exists businesses_reputation_tier_check;

alter table businesses
    drop column if exists reputation_calculated_at,
    drop column if exists average_delivery_seconds,
    drop column if exists success_rate,
    drop column if exists lost_disputes_count,
    drop column if exists business_failure_orders_count,
    drop column if exists ratings_count,
    drop column if exists reputation_tier;
