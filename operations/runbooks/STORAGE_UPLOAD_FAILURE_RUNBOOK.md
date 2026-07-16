# RUNBOOK: Private storage upload or signed URL fails

Estado de validacion: PARTIALLY VALIDATED

## SINTOMA

No se pueden subir documentos, comprobantes, adjuntos o ver signed URL.

## SEVERIDAD INICIAL

SEV-2 si bloquea ordenes/soporte/intake.

## DIAGNOSTICO

```powershell
$runId = "storage_incident_" + (Get-Date -Format "yyyyMMddHHmmss")
$env:STAGING_VALIDATION_ACK = $runId
python scripts\staging_storage_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id $runId --confirm-staging --output evidence\slice_runs\$runId.json
```

## MITIGACION

- Si bucket falta: corregir proveedor/env.
- Si signed URL falla: revisar service role y bucket privado.

## PROHIBICIONES

- No hacer bucket publico.
- No compartir `storage_path`.
