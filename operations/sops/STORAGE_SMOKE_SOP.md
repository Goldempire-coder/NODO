# SOP: Staging Storage Smoke

SOP_ID: SOP-STORAGE-001
Estado de validacion: PARTIALLY VALIDATED

## Proposito

Verificar Supabase Storage privado sin exponer `storage_path`.

## Procedimiento

```powershell
$runId = "storage_smoke_" + (Get-Date -Format "yyyyMMddHHmmss")
$env:STAGING_VALIDATION_ACK = $runId
python scripts\staging_storage_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id $runId --confirm-staging --output evidence\slice_runs\$runId.json
```

## Resultado esperado

- `checksum_match: true`.
- `object_deleted: true`.
- `storage_path_exposed: false`.
- `signed_url_persisted: false`.

## Si falla

- Revisar buckets `SUPABASE_STORAGE_BUCKET_*`.
- Revisar `PRIVATE_STORAGE_MODE=supabase`.
- Revisar `SUPABASE_SERVICE_ROLE_KEY` solo en backend.
