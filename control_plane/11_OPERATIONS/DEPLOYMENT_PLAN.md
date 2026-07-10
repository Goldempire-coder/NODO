# DEPLOYMENT_PLAN.md

Target: product ready for mass use, not a throwaway demo.

Initial scale target:

- 200 businesses
- 10,000 clients
- up to 2,000 simultaneous active orders/transactions

## Approved initial staging/production stack

Frontend:
- Next.js + TypeScript + Tailwind
- Cloudflare Pages
- Vercel is legacy/no recomendado for NODO because long-term cost may grow too quickly with usage.

Backend:
- FastAPI + Python
- Railway service for API
- Railway worker/scheduler process for jobs when enabled
- Keep Docker/VPS migration possible later if Railway cost grows.

Database:
- PostgreSQL
- Supabase Pro PostgreSQL
- connection pooling required

Storage:
- Cloudflare R2 or Supabase Storage
- private buckets
- signed URLs

Queue/cache:
- Upstash Redis
- Required for rate limits, idempotency locks and jobs.

Payments:
- Stripe Checkout for automatic credit purchases
- Zelle/USDT manual fallback

Bot:
- Telegram webhook mode
- no production polling

Observability:
- Sentry or provider-native error monitoring
- structured logs
- uptime checks
- alerting for failed jobs, webhook failures, high 500 rate and delayed notifications

## Staging/test-mode rollout order

1. Create Supabase Pro project and capture staging `DATABASE_URL`.
2. Create Upstash Redis database and capture staging `REDIS_URL`.
3. Create Railway API service with backend env vars only.
4. Create Railway worker/job process only after API smoke passes.
5. Create Cloudflare Pages project for `apps/web`.
6. Configure private storage with Cloudflare R2 or Supabase Storage.
7. Configure Stripe test mode products/prices and webhook secret.
8. Configure Telegram bot/Mini App test URL after Cloudflare Pages URL exists.
9. Run migrations against Supabase staging.
10. Run smoke tests against real staging services.
11. Run controlled small stress test against staging.
12. Owner reviews evidence before any production/live use.

## Provider ownership

- Cloudflare Pages owns frontend public env only.
- Railway owns backend secrets and API/worker runtime env.
- Supabase owns PostgreSQL and optional storage.
- Upstash owns Redis.
- Stripe owns credit purchase payments.
- Telegram owns bot/Mini App entry.

No secret may be committed to the repo.

## Production requirements

- DB connection pooling
- atomic order creation
- unique lock/constraint so two users cannot take same ad
- idempotent Stripe webhook handling
- idempotent jobs
- rate limits
- backup/restore plan
- deployment rollback plan
- no fake production metrics
- no `READY_FOR_REAL_USE` until owner approves real-service evidence
