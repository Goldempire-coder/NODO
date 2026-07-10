# DO_NOT_BUILD.md

Do not build:

- new order states
- new ad states
- direct DB updates bypassing state machines
- direct credit updates bypassing credit service
- automatic cancellation of payment_reported orders
- credit release after payment_reported without admin/state rule
- auto-complete when dispute is open
- spammy repeated notifications
- production polling Telegram bot
- real credentials or deploy
- manual remitter confirmation screen `R-10_CONFIRM_RECEIVED`
- admin dispute resolution
- real payments, escrow or guarantees of funds
- `job_name` column in job_runs
- `event_type` column for new notification_jobs migrations
- READY_FOR_REAL_USE declaration

If any required service is missing, stop with BLOCKED_BY_MISSING_CONTRACT.
