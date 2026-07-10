# Owner Audit - slice_14D_business_intake_bot

## Estado

PASSED_AFTER_OWNER_AUDIT_FIX

No se declara `READY_FOR_REAL_USE`.

## Alcance auditado

Se reviso el build report, evidencia, migracion, modulo `business_intake`, webhook Telegram, storage privado, tests y superficies publicas del slice 14D.

## Hallazgo corregido

Durante la auditoria se encontro que `POST /api/v1/business-intake/{id}/submit` aceptaba en runtime de test un rango invertido:

```txt
min_amount_usd = 500.00
max_amount_usd = 20.00
```

En PostgreSQL la constraint lo iba a rechazar, pero demasiado tarde, con riesgo de error de DB/500 en vez de error seguro. Se corrigio en service antes de persistir:

- `apps/api/app/modules/business_intake/service.py`
  - agrega validacion Decimal
  - exige `min_amount_usd > 0`
  - exige `max_amount_usd >= min_amount_usd`
  - responde `VALIDATION_ERROR`

Se agrego prueba:

- `apps/api/tests/test_business_intake_bot.py`
  - `test_submit_rejects_invalid_amount_range_before_persistence`

## Validacion ejecutada tras la correccion

```txt
python -m pytest apps\api\tests\test_business_intake_bot.py -q
8 passed, 1 warning

python scripts\run_slice_14D_tests.py
passed
8 passed, 1 warning

python -m pytest apps\api\tests -q
118 passed, 1 warning

corepack pnpm --filter @nodo/web build
passed

python -m ruff check apps\api scripts
passed

python -m compileall apps scripts
passed
```

## Invariantes confirmadas

- El bot/intake no crea negocio activo.
- El bot/intake no crea `business_access_links`.
- El bot/intake no cambia roles a `business_owner`.
- El bot/intake no da acceso a Mini App Negocio.
- El bot/intake no crea anuncios.
- El bot/intake no acredita creditos.
- Los endpoints bot estan protegidos por `X-NODO-Bot-Webhook-Secret`.
- `contact_user_id` debe coincidir con `telegram_user_id`.
- `contact_phone` y `business_phone` se guardan separados.
- Videos/MIME no permitidos responden `BOT_UPLOAD_INVALID`.
- Documentos usan storage privado mediante `file_assets.resource_type = business_intake` y `file_type = intake_document`.
- No se expone `storage_path` en schemas/routes/webhook.
- Admin accept/reject requiere RBAC, reason e idempotencia.
- Support lee, pero no acepta/rechaza.

## Observaciones no bloqueantes

- El webhook directo cubre `/start negocio` y contacto compartido; el submit completo y documentos quedan implementados como endpoints bot protegidos. Esto cumple el MVP tecnico, pero falta smoke real con Telegram.
- `storage_path` existe internamente en repository/model/storage, como corresponde para storage privado, pero no se devuelve por API publica.
- La migracion down restaura constraints previas de `file_assets`, pero conserva la columna aditiva `metadata_json`. No bloquea el slice, aunque conviene decidir en hardening si rollback debe remover columnas aditivas.
- Sigue el warning heredado `StarletteDeprecationWarning` de `httpx`.

## Resultado

El slice 14D queda aceptable para owner review despues de la correccion de validacion de montos.

```txt
PASSED_AFTER_OWNER_AUDIT_FIX
```
