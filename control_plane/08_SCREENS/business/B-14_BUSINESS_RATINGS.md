# B-14_BUSINESS_RATINGS.md

SCREEN_ID: B-14_BUSINESS_RATINGS
actor: business
slice: future_business_reputation_ui
status: CONTRACT_ONLY_NOT_BUILT

purpose:
View own backend-calculated reputation metrics.

route:
/business/ratings

entry points:
Dashboard

exit points:
B-04_BUSINESS_DASHBOARD

data required:
- authenticated user/session
- own business reputation DTO
- `reputation_tier`
- `rating_avg`
- `ratings_count`
- `completed_orders_count`
- `success_rate`
- `average_delivery_seconds`

read strategy:
- Backend returns all metrics and labels.
- Frontend does not calculate success rate, averages or tier.
- Business cannot edit reputation.

states:
- loading
- metrics_not_calculated
- empty
- error
- success

audit events:
none for read

QA checklist:
- own business only
- no internal `risk_level`
- no textual reviews
- no functional UI is built in Slice 42A
