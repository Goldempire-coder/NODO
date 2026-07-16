# ENVIRONMENT_VARIABLES.md

Secrets must never live in frontend code or repo.

## Core

- BOT_TOKEN
- BUSINESS_INTAKE_BOT_TOKEN
- JWT_SECRET
- JWT_REFRESH_SECRET
- DATABASE_URL
- API_CORS_ORIGINS
- APP_ENV
- APP_NAME
- APP_VERSION
- NODO_BUILD_ID

## Supabase PostgreSQL

- DATABASE_URL
- NODO_DB_POOL_MAX_SIZE
- NODO_DB_POOL_TIMEOUT_SECONDS
- NODO_DB_POOL_WARM_SIZE

Backend database access must use a bounded application pool. For local/staging stress, `NODO_DB_POOL_MAX_SIZE=50` was the best observed setting on the current local Docker Postgres run; `80` stayed correct but increased p95 latency, and unbounded connections previously hit PostgreSQL `too many clients`. `NODO_DB_POOL_WARM_SIZE` controls best-effort connection warmup at API boot so the first concurrent requests do not pay cold connection setup.

If Supabase Storage is used:

- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY

`SUPABASE_SERVICE_ROLE_KEY` is backend-only and must never be exposed to Cloudflare Pages.

## Storage

If Cloudflare R2 is used:

- R2_ACCOUNT_ID
- R2_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY
- R2_BUCKET_NAME
- R2_PUBLIC_BASE_URL optional if signed proxy is used

If Supabase Storage is used:

- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_STORAGE_BUCKET

Common:

- STORAGE_SIGNING_SECRET
- STORAGE_SIGNED_URL_TTL_SECONDS

## Stripe

- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_STARTER
- STRIPE_PRICE_PRO
- STRIPE_PRICE_BUSINESS
- STRIPE_PRICE_ENTERPRISE
- STRIPE_SUCCESS_URL
- STRIPE_CANCEL_URL

## Redis / queue

- REDIS_URL
- MARKETPLACE_CACHE_TTL_SECONDS
- MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS
- AUTH_USER_CACHE_TTL_SECONDS
- API_THREAD_LIMIT

Use Upstash Redis for staging/production sensitive rate limits, idempotency, job locks and shared marketplace cache invalidation. Marketplace search uses a short-lived local cache layered over a shared Redis cache namespace with versioned invalidation so ad/order mutations invalidate stale reads across workers. `MARKETPLACE_CACHE_TTL_SECONDS` controls the short-lived marketplace search cache; default is `30` seconds and the cache is cleared by marketplace-changing actions such as ad create/update/pause/archive and order creation. `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS` controls the maximum age for JWT claims-only auth on safe marketplace reads; default is `300` seconds. This claims-only path is allowed only for public-safe marketplace reads and must never be used for order creation, payment instructions, reports, chat, business operations, credits, admin, bots or any mutation. Older tokens fall back to full user repository auth. `AUTH_USER_CACHE_TTL_SECONDS` controls the short-lived runtime cache for authenticated user reads; default is `2` seconds. `API_THREAD_LIMIT` controls the AnyIO worker thread limit for synchronous FastAPI endpoints; default is `40`.

## Railway backend env

Railway must receive backend-only env vars:

- APP_ENV
- DATABASE_URL
- NODO_DB_POOL_MAX_SIZE
- NODO_DB_POOL_TIMEOUT_SECONDS
- NODO_DB_POOL_WARM_SIZE
- REDIS_URL
- MARKETPLACE_CACHE_TTL_SECONDS
- MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS
- AUTH_USER_CACHE_TTL_SECONDS
- API_THREAD_LIMIT
- BOT_TOKEN
- BUSINESS_INTAKE_BOT_TOKEN
- JWT_SECRET
- JWT_REFRESH_SECRET
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- Storage backend secrets

## Cloudflare Pages env

Cloudflare Pages must receive public env vars only:

- NEXT_PUBLIC_API_BASE_URL
- NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
- NEXT_PUBLIC_APP_ENV

Cloudflare Pages must not receive backend secrets.

## Public frontend env

Public env must only contain non-secret values:

- NEXT_PUBLIC_API_BASE_URL
- NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
- NEXT_PUBLIC_APP_ENV

## Prohibited

- BOT_TOKEN in frontend
- BUSINESS_INTAKE_BOT_TOKEN in frontend
- STRIPE_SECRET_KEY in frontend
- SUPABASE_SERVICE_ROLE_KEY in frontend
- DATABASE_URL in frontend
- REDIS_URL in frontend
- R2_SECRET_ACCESS_KEY in frontend
- hardcoded secrets in docs, tests or examples
## Observability - slice 24

Backend variables:

- `OBSERVABILITY_INGEST_ENABLED`: `0|1`, default `0`.
- `OBSERVABILITY_MODE`: `disabled|local_only|persisted|logs_only`, default `disabled`.
- `OBSERVABILITY_SAMPLE_RATE`: decimal `0` to `1`, default `0`.
- `OBSERVABILITY_EVENT_TTL_DAYS`: default `7` for staging.
- `OBSERVABILITY_MAX_EVENTS_PER_SESSION`: default `500`.
- `OBSERVABILITY_MAX_BATCH_EVENTS`: default `20`.
- `OBSERVABILITY_MAX_EVENT_BYTES`: default `2048`.

Frontend public variables:

- `NEXT_PUBLIC_APP_VERSION`
- `NEXT_PUBLIC_NODO_BUILD_ID`
- `NEXT_PUBLIC_OBSERVABILITY_ENABLED`
- `NEXT_PUBLIC_OBSERVABILITY_MODE`

Public frontend variables must not include secrets. Backend can reject ingestion even if frontend collection is enabled.
