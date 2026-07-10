# real services stack alignment

Date: 2026-07-05

Status: READY_FOR_OWNER_REVIEW

## Decision

NODO staging/production initial stack is:

- Cloudflare Pages for frontend.
- Railway for backend API and worker/jobs.
- Supabase Pro for PostgreSQL.
- Upstash Redis for locks, rate limits, idempotency and jobs.
- Cloudflare R2 or Supabase Storage for private storage.
- Stripe test mode before live.
- Telegram Mini App test mode before real use.

Vercel is legacy/no recomendado for NODO because long-term cost may grow too quickly with usage.

## Updated files

- `control_plane/README.md`
- `control_plane/00_GOVERNANCE/DECISION_LOG.md`
- `control_plane/01_PRODUCT/SPEC_MASTER.md`
- `control_plane/10_QA/DEPLOY_READINESS_GATE.md`
- `control_plane/11_OPERATIONS/DEPLOYMENT_PLAN.md`
- `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`
- `control_plane/11_OPERATIONS/REAL_SERVICES_STAGING_SETUP.md`
- `.env.staging.example`

## Guardrails

- No secrets in repo.
- Backend secrets only in Railway/provider dashboards.
- Cloudflare Pages receives public env vars only.
- `READY_FOR_REAL_USE` remains prohibited until real-service smoke, monitoring, backup/restore and owner approval.

## Next step

Start `REAL_SERVICES_SETUP / STAGING_TEST_MODE` by creating provider resources in this order:

1. Supabase Pro PostgreSQL.
2. Upstash Redis.
3. Railway API.
4. Cloudflare Pages frontend.
5. Cloudflare R2 or Supabase Storage.
6. Stripe test mode.
7. Telegram test mode.

