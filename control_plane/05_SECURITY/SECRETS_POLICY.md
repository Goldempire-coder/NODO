# SECRETS_POLICY.md

Contrato de secretos.

## Regla madre

Ningun secreto puede vivir en frontend, repositorio, logs, screenshots, fixtures publicos ni respuestas API.

## Secretos protegidos

```txt
BOT_TOKEN
BUSINESS_INTAKE_BOT_TOKEN
JWT_SECRET
JWT_REFRESH_SECRET
DATABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET
REDIS_URL
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STORAGE_ACCESS_KEY
STORAGE_SECRET_KEY
ADMIN_BOOTSTRAP_SECRET
```

## Permitido en frontend

Solo variables publicas no secretas con prefijo aprobado, por ejemplo:

```txt
NEXT_PUBLIC_APP_URL
NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
```

`SUPABASE_ANON_KEY` no reemplaza RBAC/RLS/backend authorization.

## Reglas

- Usar variables de entorno del proveedor de deploy.
- Nunca hardcodear secretos.
- Nunca imprimir secretos en logs.
- Nunca enviar secretos a Sentry/monitoring.
- Rotar secreto si se expone.
- Separar secretos por ambiente: local, staging, production.

## Tests/checks obligatorios

- escaneo de repo por patrones de secretos antes de release.
- build frontend no contiene secretos backend.
- logs de error no contienen tokens.
- webhook Stripe falla si falta o no coincide firma.
- Telegram auth falla si falta bot token backend.
- Webhook del Bot Registro Negocios falla si falta `BUSINESS_INTAKE_BOT_TOKEN` o si el secret pertenece al bot cliente.
- `BUSINESS_INTAKE_BOT_TOKEN` esta prohibido en frontend, bundles, respuestas API, audit metadata, logs y reportes publicos.

## Bloqueo

Si un secreto aparece en frontend, repo o logs, Builder debe reportar:

```txt
BLOCKED_BY_SECURITY_GAP
```
