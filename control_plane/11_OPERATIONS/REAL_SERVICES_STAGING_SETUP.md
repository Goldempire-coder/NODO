# REAL_SERVICES_STAGING_SETUP.md

Fase: `REAL_SERVICES_SETUP / STAGING_TEST_MODE`

Estado permitido: `READY_FOR_OWNER_REVIEW` despues de evidencia.

Estado prohibido: `READY_FOR_REAL_USE`.

## Stack aprobado

- Frontend: Cloudflare Pages
- Backend API: Railway
- Backend jobs/workers: Railway
- PostgreSQL: Supabase Pro
- Redis: Upstash Redis
- Storage privado: Cloudflare R2 o Supabase Storage
- Pagos de creditos: Stripe test mode primero
- Telegram: bot/Mini App en test mode primero

Vercel queda legacy/no recomendado para NODO por costo de escala.

## Orden operativo

1. Crear proyecto Supabase Pro.
2. Guardar `DATABASE_URL` solo en Railway/staging env.
3. Crear Redis en Upstash.
4. Guardar `REDIS_URL` solo en Railway/staging env.
5. Crear servicio backend en Railway.
6. Configurar env backend en Railway.
7. Correr migraciones contra Supabase staging.
8. Crear proyecto Cloudflare Pages para `apps/web`.
9. Configurar solo variables publicas en Cloudflare Pages.
10. Crear storage privado en R2 o Supabase Storage.
11. Configurar Stripe test mode y webhook de staging.
12. Configurar Telegram bot/Mini App con URL de Cloudflare Pages.
13. Correr smoke real staging.
14. Correr stress pequeno controlado staging.
15. Owner revisa evidencia.

## Variables por proveedor

### Railway API/worker

Backend-only:

- `APP_ENV=staging`
- `APP_NAME=NODO`
- `APP_VERSION`
- `NODO_BUILD_ID`
- `API_CORS_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `BOT_TOKEN`
- `BUSINESS_INTAKE_BOT_TOKEN`
- `JWT_SECRET`
- `JWT_REFRESH_SECRET`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- storage secrets according to selected provider

### Cloudflare Pages

Public-only:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME`
- `NEXT_PUBLIC_APP_ENV=staging`

Never configure backend secrets in Cloudflare Pages.

### Supabase

- PostgreSQL project
- connection string for Railway only
- optional private storage bucket if R2 is not selected

### Upstash

- Redis URL for Railway only

### Cloudflare R2

If selected:

- private bucket
- API token/key for Railway only
- no public bucket exposure for evidence, documents or payment proofs

### Stripe

Test mode first:

- products/prices for credit packages
- webhook endpoint to Railway API
- webhook signing secret in Railway only

### Telegram

Test mode first:

- Bot token in Railway only
- Mini App URL points to Cloudflare Pages staging URL
- backend validates real Telegram `initData`

## Required smoke evidence

- `/health`, `/ready`, `/version` on Railway API
- Supabase migrations apply cleanly
- Upstash Redis ping/locks/rate limits work
- private storage upload + signed view URL works
- Telegram auth from Mini App works
- Stripe test webhook credits once and duplicate webhook does not double-credit
- order flow smoke: search, create order, reveal instructions, report payment, business confirm, delivered
- job dry-run and real controlled job run are audited
- frontend build and Cloudflare Pages deploy are verified

## Hard stops

Stop and report blocker if any of these happen:

- secret appears in repo, frontend bundle, logs or API response
- migration fails against Supabase staging
- Redis lock/rate/idempotency fails against Upstash
- storage exposes `storage_path` or public evidence URL
- Stripe redirect credits without signed webhook
- Telegram auth works without backend `initData` validation
- admin mutation works without RBAC/reason/audit
- any 500 stack trace leaks to client

## Result language

Allowed:

- `READY_FOR_OWNER_REVIEW`
- `BLOCKED_BY_MISSING_SECRET`
- `BLOCKED_BY_PROVIDER_CONFIG`
- `BLOCKED_BY_MIGRATION_FAILURE`
- `BLOCKED_BY_SECURITY_GAP`
- `BLOCKED_BY_RUNTIME_BUG`

Forbidden:

- `READY_FOR_REAL_USE`
