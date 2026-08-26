# ENVIRONMENT_VARIABLES.md

Secrets must never live in frontend code or repo.

## Core

- BOT_TOKEN
- BUSINESS_INTAKE_BOT_TOKEN
- NODO_ADMIN_TELEGRAM_BOT_TOKEN
- JWT_SECRET
- JWT_REFRESH_SECRET
- DATABASE_URL
- API_CORS_ORIGINS
- APP_ENV
- APP_NAME
- RAILWAY_GIT_COMMIT_SHA (Railway-provided release source when available)
- APP_VERSION (manual fallback outside Railway)
- NODO_BUILD_ID (manual fallback outside Railway)
- TELEGRAM_WEB_APP_URL

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
- CHAT_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- CHAT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- CHAT_DUPLICATE_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- CHAT_DUPLICATE_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- CHAT_ATTACHMENT_RATE_LIMIT_MAX_ATTEMPTS
- CHAT_ATTACHMENT_RATE_LIMIT_WINDOW_SECONDS
- SUPPORT_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- SUPPORT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- SUPPORT_DUPLICATE_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- SUPPORT_DUPLICATE_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- SUPPORT_ATTACHMENT_RATE_LIMIT_MAX_ATTEMPTS
- SUPPORT_ATTACHMENT_RATE_LIMIT_WINDOW_SECONDS
- AUTH_USER_CACHE_TTL_SECONDS
- API_THREAD_LIMIT

Use Upstash Redis for staging/production sensitive rate limits, idempotency, job locks and shared marketplace cache invalidation. Marketplace search uses a short-lived local cache layered over a shared Redis cache namespace with versioned invalidation so ad/order mutations invalidate stale reads across workers. `MARKETPLACE_CACHE_TTL_SECONDS` controls the short-lived marketplace search cache; default is `30` seconds and the cache is cleared by marketplace-changing actions such as ad create/update/pause/archive and order creation. `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS` controls the maximum age for JWT claims-only auth on safe marketplace reads; default is `300` seconds. This claims-only path is allowed only for public-safe marketplace reads and must never be used for order creation, payment instructions, reports, chat, business operations, credits, admin, bots or any mutation. Older tokens fall back to full user repository auth. `AUTH_USER_CACHE_TTL_SECONDS` remains as a legacy compatibility setting but is not an authorization source: private operations and mutations reload current user status from the repository. `API_THREAD_LIMIT` controls the AnyIO worker thread limit for synchronous FastAPI endpoints; default is `40`.

Chat and Support anti-loop limits are backend-only. Defaults: chat/support
messages `10/60s`, repeated normalized message bodies `2/60s`, and attachments
`6/60s`. Duplicate-body limiter keys must use a hash, never raw message text.

## Railway backend env

Railway must receive backend-only env vars:

- APP_ENV
- APP_NAME
- NODO_RELEASE_COMMIT_SHA (explicit release source for CLI/manual deploys)
- RAILWAY_GIT_COMMIT_SHA (provided automatically for GitHub-triggered deploys)
- APP_VERSION (optional non-Railway fallback)
- NODO_BUILD_ID (optional non-Railway fallback)
- DATABASE_URL
- NODO_DB_POOL_MAX_SIZE
- NODO_DB_POOL_TIMEOUT_SECONDS
- NODO_DB_POOL_WARM_SIZE
- REDIS_URL
- MARKETPLACE_CACHE_TTL_SECONDS
- MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS
- CHAT_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- CHAT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- CHAT_DUPLICATE_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- CHAT_DUPLICATE_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- CHAT_ATTACHMENT_RATE_LIMIT_MAX_ATTEMPTS
- CHAT_ATTACHMENT_RATE_LIMIT_WINDOW_SECONDS
- SUPPORT_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- SUPPORT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- SUPPORT_DUPLICATE_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS
- SUPPORT_DUPLICATE_MESSAGE_RATE_LIMIT_WINDOW_SECONDS
- SUPPORT_ATTACHMENT_RATE_LIMIT_MAX_ATTEMPTS
- SUPPORT_ATTACHMENT_RATE_LIMIT_WINDOW_SECONDS
- AUTH_USER_CACHE_TTL_SECONDS
- API_THREAD_LIMIT
- BOT_TOKEN
- BUSINESS_INTAKE_BOT_TOKEN
- NODO_ADMIN_TELEGRAM_BOT_TOKEN
- JWT_SECRET
- JWT_REFRESH_SECRET
- TELEGRAM_WEB_APP_URL
- ORDER_NOTIFICATION_SENDER_ENABLED
- ORDER_NOTIFICATION_SENDER_INTERVAL_SECONDS
- ORDER_NOTIFICATION_SENDER_BATCH_SIZE
- BASE_RPC_URL
- NODO_CREDIT_RECEIVING_WALLET_BASE
- NODO_CREDIT_PAYMENT_NETWORK
- NODO_CREDIT_PAYMENT_CONTRACT_ADDRESS
- NODO_CREDIT_PAYMENT_CONTRACT_VERSION
- NODO_CREDIT_PAYMENT_CONTRACT_PAUSED
- NODO_CREDIT_AUTH_SIGNER_KEY
- NODO_CREDIT_AUTH_SIGNER_ADDRESS
- NODO_CREDIT_AUTH_SIGNER_VERSION
- ONCHAIN_CREDIT_AUTHORIZATION_TTL_MINUTES
- ONCHAIN_CREDIT_MIN_CONFIRMATIONS
- ONCHAIN_CREDIT_PURCHASE_TTL_MINUTES
- ONCHAIN_CREDIT_WATCHER_ENABLED
- ONCHAIN_CREDIT_WATCHER_INTERVAL_SECONDS
- ONCHAIN_CREDIT_WATCHER_BATCH_SIZE
- ONCHAIN_CREDIT_WATCHER_TIMEOUT_SECONDS
- LEGACY_CREDIT_PAYMENT_METHODS_ENABLED
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- Storage backend secrets

### Control de cambio de wallet de creditos

`NODO_CREDIT_RECEIVING_WALLET_BASE` es una direccion publica, pero cambiarla
modifica el destino de cobro. Solo se configura en backend. No debe existir como
`NEXT_PUBLIC_*`, payload editable, endpoint de configuracion ni valor hardcoded.

Antes de cambiarla en cualquier entorno registrar sin secretos:

- actor y aprobacion Owner;
- entorno y build/commit;
- fingerprint enmascarado anterior y nuevo;
- motivo y ventana;
- verificacion EVM de la direccion;
- evidencia de compra temporal controlada;
- rollback a la configuracion anterior.

NODO no almacena private key, seed phrase, mnemonic ni signing key de esa wallet.

### Signer de autorizaciones de compra crypto

52C introduce un signer operacional separado para autorizar pagos por contrato:

- `NODO_CREDIT_PAYMENT_NETWORK`
- `NODO_CREDIT_PAYMENT_CONTRACT_ADDRESS`
- `NODO_CREDIT_PAYMENT_CONTRACT_VERSION`
- `NODO_CREDIT_PAYMENT_CONTRACT_PAUSED`
- `NODO_CREDIT_AUTH_SIGNER_KEY`
- `NODO_CREDIT_AUTH_SIGNER_ADDRESS`
- `NODO_CREDIT_AUTH_SIGNER_VERSION`
- `ONCHAIN_CREDIT_AUTHORIZATION_TTL_MINUTES`
- `CREDIT_CONTRACT_RATE_LIMIT_USER_MAX_ATTEMPTS` (default `5`)
- `CREDIT_CONTRACT_RATE_LIMIT_BUSINESS_MAX_ATTEMPTS` (default `5`)
- `CREDIT_CONTRACT_RATE_LIMIT_IP_MAX_ATTEMPTS` (default `20`)
- `CREDIT_CONTRACT_RATE_LIMIT_WINDOW_SECONDS` (default `600`)
- `CREDIT_CONTRACT_PENDING_PURCHASE_LIMIT` (default `3`)

Los limites contractuales se aplican en backend. Staging/produccion requieren el
limitador Redis compartido y fallan cerrado si no esta disponible. La IP se usa
solo como clave hasheada; no se agrega en claro a logs o audit. Estas variables
solo pueden endurecer la politica: runtime limita intentos a `5/5/20`, exige una
ventana minima de `600` segundos y nunca permite mas de `3` compras pendientes.
Para compras contractuales, el limitador usa la IP agregada por el proxy final en
`X-Forwarded-For` y cae al cliente ASGI si no existe ese header. El valor se
hashea antes de usarse como clave y no se registra en claro.

Clasificacion:

- `NODO_CREDIT_PAYMENT_NETWORK` es autoridad backend obligatoria y solo acepta
  `base_sepolia` o `base_mainnet`. No se infiere desde `APP_ENV`, no se expone
  como selector frontend y un valor ausente/desconocido deshabilita el flujo;
- 52C2D-S0 debe usar `base_sepolia`. Cambiar a `base_mainnet` requiere otro gate
  Owner y no activa automaticamente frontend, watcher, wallet o fondos reales;
- direccion/version/paused, signer address/version y TTL son configuracion
  backend; no son secretos, pero no pueden venir del cliente ni actuar como
  `NEXT_PUBLIC_*`;
- `NODO_CREDIT_RECEIVING_WALLET_BASE` es la treasury publica esperada por el
  contrato y sigue el control de cambio de wallet de esta seccion;
- `NODO_CREDIT_AUTH_SIGNER_KEY` es secreto y solo se permite para signer
  temporal local/testnet;
- `LEGACY_CREDIT_PAYMENT_METHODS_ENABLED` debe quedar `false` para el flujo
  normal y para cualquier trafico real controlado.

Restricciones:

- no es treasury;
- no es owner/multisig;
- no mueve fondos;
- solo firma `PaymentAuthorization` construida por backend;
- no existe endpoint para firmar payload arbitrario;
- nunca se expone en frontend, logs, audit, screenshots o respuestas API;
- produccion no debe usar private key plana en Railway/env como custodia final;
- staging/testnet puede usarla temporalmente con wallet no oficial, monto pequeno
  y rotacion antes de produccion.

Produccion queda bloqueada hasta contratar e implementar un signer externo,
KMS o HSM. Los nombres/configuracion de ese adaptador se definen en un slice de
infra separado; no se reutiliza `NODO_CREDIT_AUTH_SIGNER_KEY` como solucion
production-ready.

When `NODO_RELEASE_COMMIT_SHA` is a valid commit SHA, it is authoritative for
CLI/manual deploys. Otherwise, when `RAILWAY_GIT_COMMIT_SHA` is a valid commit
SHA, it is authoritative over the manual fallback labels. Runtime metadata is exposed as
`version=<APP_ENV>-<short_sha>` and `build_id=<full_sha>` by both root and
`/api/v1` health/version routes. A Railway deployment without a valid Git SHA
reports `<APP_ENV>-unknown` and `unknown` rather than reusing stale manual
labels. Outside Railway, local/test environments fall back to `local`; other
environments use explicit `APP_VERSION` and `NODO_BUILD_ID`, or `unknown` when
those labels are absent.

## Cloudflare Pages env

Cloudflare Pages must receive public env vars only:

- NEXT_PUBLIC_API_BASE_URL
- NEXT_PUBLIC_APP_URL
- NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
- NEXT_PUBLIC_APP_ENV
- NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY

Cloudflare Pages must not receive backend secrets.

## Public frontend env

Public env must only contain non-secret values:

- NEXT_PUBLIC_API_BASE_URL
- NEXT_PUBLIC_APP_URL
- NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
- NEXT_PUBLIC_APP_ENV
- NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY

## Prohibited

- BOT_TOKEN in frontend
- BUSINESS_INTAKE_BOT_TOKEN in frontend
- NODO_ADMIN_TELEGRAM_BOT_TOKEN in frontend
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

- `NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED`

Public frontend variables must not include secrets. Backend can reject ingestion even if frontend collection is enabled.
