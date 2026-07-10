# REAL BACKEND SMOKE - 2026-07-08

## Estado

PASSED

No se declara READY_FOR_REAL_USE.

## Target

- Backend: `https://nodo-api-production.up.railway.app`
- Base de datos: Supabase/PostgreSQL real de staging
- Redis: Upstash/Redis real de staging
- Evidencia JSON: `evidence/slice_runs/real_backend_smoke_20260708132358.json`

## Resultado

El smoke real de backend cerró limpio:

- `GET /health`: OK
- `GET /ready`: OK
- `GET /version`: OK
- `POST /api/v1/auth/telegram`: OK con usuario admin firmado
- `GET /api/v1/admin/business-intake`: OK
- `POST /api/v1/business-intake/start`: OK
- `POST /api/v1/business-intake/{id}/contact`: OK
- `POST /api/v1/business-intake/{id}/submit`: OK
- `GET /api/v1/admin/business-intake/{id}`: OK
- `POST /api/v1/admin/business-intake/{id}/accept`: OK con `create_business=true` y `public_business_name`
- Limpieza de datos sintéticos: OK

## Invariantes Verificadas

- El negocio creado desde intake quedó `pending`.
- No se creó `business_access_link`.
- El nombre público enviado por admin quedó como nombre visible del negocio.
- Los datos sintéticos creados por el smoke fueron limpiados.

## Latencias Del Run Final

- `health`: 356.947 ms
- `ready`: 985.716 ms
- `version`: 129.177 ms
- `auth_admin_telegram`: 1007.452 ms
- `admin_intake_list`: 755.649 ms
- `intake_start`: 1870.813 ms
- `intake_contact`: 938.233 ms
- `intake_submit`: 915.387 ms
- `admin_intake_detail`: 1146.423 ms
- `admin_accept_create_business_public_name`: 2851.373 ms

## Hallazgos Durante Intentos Previos

1. El token local del bot de negocios no coincide con el token activo en Railway.
   - El secreto calculado desde `.local/business_intake_bot_token_LOCAL_ONLY.txt` devolvió `403 FORBIDDEN`.
   - El secreto activo desplegado en Railway sí permitió ejecutar el smoke.
   - Acción recomendada: alinear `BUSINESS_INTAKE_BOT_TOKEN` entre Railway y el archivo local autorizado.

2. `POST /api/v1/business-intake/start` devuelve `id`, mientras el flujo webhook usa `intake_id`.
   - No bloquea el flujo.
   - Acción recomendada: normalizar la respuesta o documentar la diferencia.

3. El endpoint REST de submit exige valores canónicos.
   - `operation`: `buy_usd`, `sell_usd`, `both`
   - `methods`: `zelle`, `usdt_trc20`
   - El bot conversacional normaliza texto natural, pero el endpoint directo no.
   - Acción recomendada: mantener canonical interno o reutilizar normalización en endpoints bot-protegidos.

4. Un intento previo falló en cleanup por orden de llaves foráneas.
   - Se corrigió el orden de limpieza en el run final.

## Riesgos Residuales

- Smoke no equivale a stress test real.
- No se probó envío real Telegram end-to-end en este run.
- No se probó upload real de documento desde Telegram en este run.
- No se declara producto listo para uso real.

