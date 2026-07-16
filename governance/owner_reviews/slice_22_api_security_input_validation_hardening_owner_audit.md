# SLICE_22_API_SECURITY_INPUT_VALIDATION_HARDENING_OWNER_AUDIT

Fecha: 2026-07-11
Estado: PASSED_AFTER_OWNER_AUDIT_FIX_WITH_LIMITS
Decision: API READY WITH LIMITS

## Alcance auditado

Se audito el resultado del builder para `slice_22_api_security_input_validation_hardening`.

Areas revisadas:

- Request schemas estrictos.
- Webhooks Telegram.
- Upload endpoints.
- IDs y listas anidadas en payloads JSON.
- Tests negativos de validacion.
- Error safety y scans de datos sensibles.

No se ejecuto DAST externo, fuzzing exhaustivo contra todas las rutas, staging real ni deploy.

## Hallazgos corregidos

### API-P1-001 - Upload endpoints leian el archivo completo antes de validar tamano

Impacto:

- Varias rutas usaban `await file.read()` completo.
- Aunque el servicio luego rechazara archivos mayores a 5 MB, el proceso ya habia cargado todo el contenido en memoria.
- Un atacante podia enviar un multipart grande y forzar consumo innecesario de memoria antes de la validacion de dominio.

Fix:

- Agregado `read_limited_upload(...)` en `apps/api/app/shared/validation.py`.
- Las rutas ahora leen como maximo `max_bytes + 1` y rechazan antes de entrar al servicio.

Rutas endurecidas:

- `apps/api/app/modules/chat/routes.py`
- `apps/api/app/modules/orders/payment_routes.py`
- `apps/api/app/modules/credits/routes.py`
- `apps/api/app/modules/business_intake/routes.py`
- `apps/api/app/modules/support/routes.py`

Validacion:

- Scan `rg -n "await file\.read\(\)" apps/api/app/modules apps/api/app/routes` -> `ROUTE_UPLOAD_FULL_READ_SCAN_CLEAN`.
- Test `test_upload_routes_reject_oversized_file_before_domain_lookup`.

### API-P2-001 - IDs en payloads anidados tenian cantidad limitada, pero no tamano por item

Impacto:

- Campos como `attachment_ids`, `evidence_file_ids`, `document_file_ids`, `proof_file_id`, `pending_payment_report_id`, `business_id` y `user_id` podian aceptar strings grandes.
- El riesgo principal era payload amplification y mayor presion sobre logs, validacion, repositorios y storage lookups.

Fix:

- Agregado `ResourceId` compartido con max length 80 en `apps/api/app/shared/validation.py`.
- Aplicado en schemas de orders, chat, support, disputes, businesses, credits y staff.

Validacion:

- Test `test_nested_attachment_ids_reject_oversized_items`.

### API-P2-002 - Auth aceptaba `init_data` y refresh tokens sin max length

Impacto:

- `init_data` de Telegram y refresh/logout tokens no tenian limites de longitud en schema.
- El backend validaba firma/estado despues, pero el borde de API podia aceptar strings arbitrariamente grandes.

Fix:

- `TelegramAuthRequest.init_data` limitado a 8192 chars.
- `RefreshRequest.refresh_token` y `LogoutRequest.refresh_token` limitados a 16-512 chars.

Validacion:

- Test `test_auth_rejects_oversized_init_data_before_signature_validation`.

## Validaciones ejecutadas

```text
python -m pytest apps\api\tests\test_api_input_validation_hardening.py -q --tb=short
8 passed, 1 warning

python -m pytest apps\api\tests -q --tb=short
209 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed!

python -m compileall apps\api apps\web\src scripts
OK

corepack pnpm --filter @nodo/web build
OK
```

Scans:

```text
FRONTEND_SECRET_SCAN_CLEAN
ROUTE_UPLOAD_FULL_READ_SCAN_CLEAN
```

El scan de evidencia solo encontro menciones descriptivas a `stack trace`, `storage_path` y `account_value` dentro de comandos/reportes. No se encontraron valores sensibles reales.

## Riesgos residuales

- No se ejecuto DAST/fuzzing externo contra las 91 rutas.
- Algunos query/path params aun se validan de forma local en cada ruta con `Query(...)` o por logica de servicio, no mediante un modelo central unico.
- No se verificaron limites de payload a nivel servidor/proxy/cloud para todos los content types.
- No se hizo staging real ni pruebas contra infraestructura cloud.
- No se hizo inventario exhaustivo automatizado de OpenAPI vs contratos.

## Veredicto

API READY WITH LIMITS.

El hardening del builder mejora la validacion de bodies y webhooks. El owner audit agrego proteccion real contra uploads grandes antes de entrar al dominio y cerro limites de IDs anidados/tokens. Todavia no alcanza para `API READY FOR PRODUCTION` sin DAST/fuzzing, staging real y cierre completo de path/query limits.
