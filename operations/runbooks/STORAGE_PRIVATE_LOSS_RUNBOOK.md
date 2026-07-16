# RUNBOOK: Private storage loss

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

- Signed URL falla para documentos/evidencia.
- Storage smoke falla.
- `file_assets` existe pero objeto no aparece en storage.

## Severidad inicial

SEV-1 si afecta evidencia de pagos, documentos privados o soporte activo.
SEV-2 si afecta solo documentos degradables no criticos.

## Primeros cinco minutos

1. Confirmar si falla storage completo o bucket especifico.
2. Revisar provider status.
3. No generar URLs publicas.
4. Guardar evidencia sin `storage_path` completo ni signed URLs.

## Diagnostico

```powershell
python scripts\staging_storage_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id storage_loss_<timestamp> --confirm-staging --output evidence\slice_runs\storage_loss_<timestamp>.json
```

## Recuperacion

Usar `STORAGE_RESTORE_SOP.md`.

## Prohibiciones

- No copiar objetos privados a bucket publico.
- No pegar signed URLs en tickets/chat.
- No borrar `file_assets` para ocultar mismatch.
