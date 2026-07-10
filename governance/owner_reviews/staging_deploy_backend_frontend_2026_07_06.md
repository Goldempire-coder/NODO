# NODO staging deploy - backend + frontend

Fecha: 2026-07-06

Estado: `STAGING_BACKEND_FRONTEND_DEPLOYED`

No se declara `READY_FOR_REAL_USE`.

## Backend Railway

- Project: `nodo-api-staging`
- Service: `nodo-api`
- Railway status: `Online`
- Public URL: `https://nodo-api-production.up.railway.app`
- Runtime port: `8080`
- Config files added:
  - `Dockerfile`
  - `.dockerignore`
  - `railway.json`

## Backend smoke

Public smoke passed:

```txt
GET /health 200
GET /ready 200
GET /version 200
```

Observed `/version`:

```txt
service: NODO
version: 0.1.0-staging
build_id: railway-staging-20260706-01
environment: staging
```

Observed `/ready`:

```txt
database.ok = true
redis.ok = true
```

## CORS

Allowed staging origins:

```txt
http://localhost:3000
https://nodo-staging.pages.dev
https://cd56ce3c.nodo-staging.pages.dev
```

Preflight smoke:

```txt
Origin: https://nodo-staging.pages.dev
OPTIONS /api/v1/auth/telegram
Status: 200
Access-Control-Allow-Origin: https://nodo-staging.pages.dev
```

## Frontend Cloudflare Pages

- Project: `nodo-staging`
- URL: `https://nodo-staging.pages.dev`
- Preview deployment: `https://cd56ce3c.nodo-staging.pages.dev`
- Output directory: `apps/web/out`

Frontend changes:

- `apps/web/src/lib/env.ts` now resolves `NEXT_PUBLIC_API_BASE_URL`.
- `apps/web/src/api/client.ts` now prefixes API requests with the configured API base URL.
- `apps/web/src/api/auth.ts` now prefixes Telegram auth request with the configured API base URL.
- `apps/web/next.config.mjs` now uses static export for Cloudflare Pages.

## Frontend build

Build command:

```txt
NEXT_PUBLIC_API_BASE_URL=https://nodo-api-production.up.railway.app
NEXT_PUBLIC_APP_ENV=staging
corepack pnpm --filter @nodo/web build
```

Result:

```txt
Compiled successfully
Exporting static pages OK
apps/web/out/index.html found
```

## Secret scan

Local frontend output scan found no hits for:

```txt
SUPABASE_SERVICE_ROLE_KEY
STRIPE_SECRET_KEY
JWT_SECRET
JWT_REFRESH_SECRET
BOT_TOKEN
service_role
storage_path
postgresql://
redis://
```

## Known remaining work

- Configure Telegram Mini App real entry to `https://nodo-staging.pages.dev`.
- Run Telegram real smoke from the app, not only browser HTTP.
- Run staging API workflow smoke through Railway + Cloudflare.
- Run staging concurrency/stress at controlled profile after Telegram smoke.
- Configure custom domain later if owner wants it.
- Update CORS when final production/frontend domain changes.
- Do not authorize real users until owner explicitly declares `READY_FOR_REAL_USE`.
