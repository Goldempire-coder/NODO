# SOP: Post Deploy Verification

SOP_ID: SOP-POSTDEPLOY-001
Estado de validacion: PARTIALLY VALIDATED

## Proposito

Verificar que un deploy quedo operativo.

## Procedimiento

1. Health:
   ```powershell
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/health" -Headers @{"X-Request-Id"="postdeploy_health_<timestamp>"}
   ```
2. Readiness:
   ```powershell
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/ready" -Headers @{"X-Request-Id"="postdeploy_ready_<timestamp>"}
   ```
3. Version:
   ```powershell
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/version" -Headers @{"X-Request-Id"="postdeploy_version_<timestamp>"}
   ```
4. Si env real existe, validar schema:
   ```powershell
   python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\postdeploy_schema.json
   ```
5. Si storage fue tocado:
   ```powershell
   python scripts\staging_storage_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id postdeploy_storage_<timestamp> --confirm-staging --output evidence\slice_runs\postdeploy_storage.json
   ```

## Resultado esperado

- Health `status=ok`.
- Ready `status=ready`.
- Version/build esperado.
- No `storage_path` expuesto.

## Falla

Abrir runbook correspondiente.
