# NODO Telegram bot staging setup

Fecha: 2026-07-06

Estado: `TELEGRAM_STAGING_BOT_CONFIGURED`

No se declara `READY_FOR_REAL_USE`.

## Bot

- Bot username: `@NodoCambioBot`
- Bot API `getMe`: OK
- Token real: no documentado ni expuesto.

## Mini App URL

Configured Telegram chat menu button:

```txt
text: Abrir NODO
url: https://nodo-staging.pages.dev
```

Telegram API calls completed:

```txt
setChatMenuButton ok=True
setMyCommands ok=True
setMyDescription ok=True
setMyShortDescription ok=True
```

## Backend

Railway backend redeployed with real `BOT_TOKEN`.

Smoke:

```txt
GET /ready: ready
GET /version: 0.1.0-staging / railway-staging-20260706-01 / staging
```

Security negative smoke:

```txt
POST /api/v1/auth/telegram with fake initData
Result: 401 Unauthorized
```

## Next required validation

Open `@NodoCambioBot` in Telegram, press `Abrir NODO`, and confirm:

- The Mini App opens inside Telegram.
- Welcome screen loads.
- Telegram `initData` is present.
- Auth succeeds with the real bot token.
- No browser-only fallback is required.

After that, run staging workflow smoke through the real Telegram Mini App.

## 2026-07-06 fix: API base URL in static frontend

Issue observed in Telegram:

```txt
No pudimos conectar con el servicio
```

Root cause:

```txt
The static frontend was reading NEXT_PUBLIC_API_BASE_URL through dynamic process.env[key].
Next.js did not inline that dynamic access into the browser bundle, so the frontend called /api/v1/... on Cloudflare Pages instead of Railway.
```

Fix:

```txt
apps/web/src/lib/env.ts now reads NEXT_PUBLIC_* variables through direct process.env.NEXT_PUBLIC_* access.
apps/web was rebuilt with NEXT_PUBLIC_API_BASE_URL=https://nodo-api-production.up.railway.app.
Cloudflare Pages was redeployed.
```

Verification:

```txt
Production page JS: /_next/static/chunks/app/page-7077f56e733facef.js
Published JS contains: https://nodo-api-production.up.railway.app
Secret scan against frontend output: no server secret hits.
```

New Cloudflare preview:

```txt
https://db799eab.nodo-staging.pages.dev
```
