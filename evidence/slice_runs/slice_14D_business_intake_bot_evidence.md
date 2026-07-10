# Evidence - slice_14D_business_intake_bot

## Estado
READY_FOR_OWNER_REVIEW

## Construido
- Modulo backend `business_intake`.
- Migracion reversible `0014_slice_14D_business_intake_bot`.
- Endpoints bot/admin para intake.
- Extension del webhook Telegram para `/start negocio` y contacto compartido.
- Storage privado para documentos de intake mediante `file_assets`.
- Runner `scripts/run_slice_14D_tests.py`.

## Verificaciones exactas
- `python scripts\run_slice_14D_tests.py`: passed, `7 passed, 1 warning in 2.04s`.
- `$env:PYTHONPATH='apps/api;C:\Users\carlo\AppData\Roaming\Python\Python314\site-packages'; python -m pytest apps\api\tests -q`: `117 passed, 1 warning in 23.38s`.
- `corepack pnpm --filter @nodo/web build`: passed, Next.js 15.5.20 compiled and exported successfully.
- `python -m ruff check apps\api scripts`: `All checks passed!`.
- `python -m compileall apps scripts`: passed.

## Scans
- `rg -n "BOT_TOKEN|SUPABASE_SERVICE_ROLE_KEY|JWT_SECRET|JWT_REFRESH_SECRET|storage_path|account_value|escrow|fondos protegidos|pago garantizado|garantia de entrega|NODO recibio dinero" apps\web\src apps\web\out`: no hits.
- `rg -n "storage_path|account_value" apps\api\app\modules\business_intake\schemas.py apps\api\app\modules\business_intake\routes.py apps\api\app\routes\telegram_bot.py`: no hits.

## Invariantes cubiertas
- `/start negocio` no crea negocio.
- Contacto compartido requerido y validado contra Telegram user id.
- Submit crea `business_intake_requests` en `submitted`.
- Update duplicado no duplica solicitud ni documento.
- Upload MIME valido funciona.
- Video/MIME invalido falla con `BOT_UPLOAD_INVALID`.
- Archivo mayor a 5 MB falla.
- API no expone `storage_path`.
- Admin list/detail aplica masking.
- Admin accept/reject requieren reason/idempotencia/RBAC.
- Support no acepta/rechaza.
- Bot no crea businesses.
- Bot no cambia `users.role`.
- Bot no crea `business_access_links`.
- Audit events cubiertos.

## Riesgos residuales
- No hubo smoke real contra Telegram ni storage real.
- El flujo conversacional completo de formulario/documentos se apoya en endpoints bot protegidos; el webhook directo cubre inicio y contacto.
- Warning Starlette/httpx heredado.
