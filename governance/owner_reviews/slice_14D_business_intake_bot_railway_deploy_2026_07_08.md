# slice_14D business intake bot - Railway deploy

## Estado

DEPLOYED_TO_STAGING_BACKEND

No se declara `READY_FOR_REAL_USE`.

## Railway

- Project: `nodo-api-staging`
- Service: `nodo-api`
- URL: `https://nodo-api-production.up.railway.app`
- Deployment ID: `4028b7ab-308d-4222-a199-21da1890904d`

## Configuracion aplicada

Variable confirmada en Railway:

```txt
SUPABASE_STORAGE_BUCKET_BUSINESS_INTAKE=business-intake
```

Variables sensibles confirmadas por nombre, sin imprimir valores:

```txt
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
BOT_TOKEN
DATABASE_URL
REDIS_URL
```

## Migraciones reales aplicadas en Supabase/Postgres

```txt
0013_slice_14B1_business_access_links.up.sql
0014_slice_14D_business_intake_bot.up.sql
```

Tablas verificadas:

```txt
business_access_links = true
business_intake_requests = true
```

## Verificacion backend

```txt
GET /health
status ok

GET /ready
database ok
redis ok

GET /version
environment staging
```

## Verificacion endpoint 14D

Antes del deploy:

```txt
POST /api/v1/business-intake/start
404 Not Found
```

Despues del deploy:

```txt
POST /api/v1/business-intake/start sin X-NODO-Bot-Webhook-Secret
403 FORBIDDEN
```

Esto confirma que el endpoint existe y esta protegido.

## Verificacion Telegram webhook

`getWebhookInfo` confirmado sin exponer token ni URL secreta:

```txt
ok = true
has_webhook_url = true
points_to_railway_api = true
pending_update_count = 0
last_error = false
allowed_updates = message, edited_message
```

## Siguiente paso

Smoke real desde Telegram:

```txt
/start negocio
compartir contacto propio
confirmar que el bot responde el flujo de solicitud
```

Luego probar submit/documentos mediante flujo protegido del bot/endpoints y revisar cola admin.
