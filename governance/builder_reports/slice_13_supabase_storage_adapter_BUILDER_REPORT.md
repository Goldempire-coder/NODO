# BUILDER_REPORT - slice_13_supabase_storage_adapter

Estado final: `READY_FOR_OWNER_REVIEW`

No se declara `READY_FOR_REAL_USE`.

## Resumen

Se construyo el adaptador privado de Supabase Storage para staging/produccion manteniendo intactas las superficies publicas existentes. Los endpoints, payloads, copy, disclaimers y reglas de negocio no cambiaron.

La implementacion usa `httpx`, dependencia ya disponible en el entorno, por lo que no se instalaron dependencias nuevas.

## Archivos creados/modificados

- `.env.staging.example`
  - Activa `PRIVATE_STORAGE_MODE=supabase` para staging template.
  - Agrega buckets canonicos:
    - `SUPABASE_STORAGE_BUCKET_BUSINESS_VERIFICATION=business-verification`
    - `SUPABASE_STORAGE_BUCKET_PAYMENT_EVIDENCE=payment-evidence`
    - `SUPABASE_STORAGE_BUCKET_CREDIT_PURCHASE_PROOFS=credit-purchase-proofs`
    - `SUPABASE_STORAGE_BUCKET_MESSAGE_ATTACHMENTS=message-attachments`
- `apps/api/app/core/config.py`
  - Agrega validacion obligatoria de `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` cuando `PRIVATE_STORAGE_MODE=supabase`.
  - Agrega settings para los cuatro buckets privados.
- `apps/api/app/main.py`
  - Agrega `build_private_storage(settings)`.
  - Activa `SupabasePrivateStorage` en runtime no-test cuando `PRIVATE_STORAGE_MODE=supabase`.
- `apps/api/app/shared/storage/private.py`
  - Agrega `SupabasePrivateStorage`.
  - Implementa upload privado por bucket.
  - Implementa signed URL corta con TTL maximo de 300 segundos.
  - Devuelve errores seguros sin detalles del proveedor.
- `apps/api/tests/test_supabase_storage_adapter.py`
  - Pruebas mockeadas de upload, bucket mapping, signed URL, errores seguros, env validation y activacion desde `main.py`.
- `evidence/slice_runs/slice_13_supabase_storage_adapter_evidence.md`
- `evidence/slice_runs/slice_13_supabase_storage_adapter_test_results.json`

## Contratos cumplidos

- Buckets privados soportados:
  - `business-verification`
  - `payment-evidence`
  - `credit-purchase-proofs`
  - `message-attachments`
- No se crean buckets publicos.
- `SUPABASE_SERVICE_ROLE_KEY` es backend-only.
- No se expone `storage_path` en frontend/bundle.
- No se persisten signed URLs.
- Signed URL limitada a maximo 300 segundos.
- Upload/sign usan errores seguros:
  - `STORAGE_UNAVAILABLE`
  - `STORAGE_UPLOAD_FAILED`
  - `BUSINESS_DOCUMENT_NOT_FOUND`
- No se cambiaron endpoints ni payloads publicos.
- No se tocaron reglas de negocio.

## Dependencias

No se instalaron dependencias nuevas.

`httpx` ya estaba disponible (`0.28.1`) y se uso para llamadas HTTP directas a Supabase Storage.

## Pruebas ejecutadas

| Comando | Resultado |
| --- | --- |
| `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_supabase_storage_adapter.py -q` | `6 passed in 1.47s` |
| `python -m ruff check apps\api scripts` | `All checks passed!` |
| `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` | `98 passed, 1 warning in 23.26s` |
| `python -m compileall apps scripts` | exit code `0` |
| `corepack pnpm --filter @nodo/web build` | exit code `0` |

Warning conocido:

- `StarletteDeprecationWarning` por `fastapi.testclient`/`httpx`; no bloquea segun contexto heredado.

## Escaneo de secretos/datos privados

Comando:

```powershell
rg -n "SUPABASE_SERVICE_ROLE_KEY|service-role|supabase://|storage_path|signedURL|signedUrl|account_value" apps/web/src apps/web/.next
```

Resultado: sin matches.

Comando:

```powershell
rg -n "service-role|sk_live_|whsec_live|BEGIN PRIVATE KEY|storage_path|account_value" apps/web/src apps/web/.next
```

Resultado: sin matches.

## Tests no ejecutados

- Smoke real contra Supabase Storage: no ejecutado porque no existe `.local/supabase_storage_LOCAL_ONLY.txt`.
- No se uso Supabase real ni servicios reales desde este slice.

## Riesgos residuales

- Falta validar con credenciales locales autorizadas que los buckets reales aceptan upload y signed URL.
- Falta verificar politicas/permisos reales del proyecto Supabase en staging.
- El producto sigue sin estar autorizado como `READY_FOR_REAL_USE`.

## Scope no construido

- No se tocaron endpoints.
- No se tocaron payloads publicos.
- No se tocaron copy/disclaimers.
- No se tocaron reglas de negocio.
- No se tocaron servicios reales.
- No se hizo deploy.
- No se avanzo a otro slice.

## Estado final

`READY_FOR_OWNER_REVIEW`
