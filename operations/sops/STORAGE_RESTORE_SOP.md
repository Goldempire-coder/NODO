# SOP: Storage Restore

SOP_ID: SOP-STORAGE-RESTORE-001
Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Proposito

Restaurar objetos privados de NODO y validar que coinciden con `file_assets` sin exponer `storage_path` ni signed URLs persistidas.

## Alcance

- business verification documents.
- payment evidence.
- credit purchase proofs.
- message attachments.
- business intake documents.
- support attachments.

## Cuando usar

- Restore drill de storage.
- Perdida/corrupcion de objetos privados.
- Restore DB que requiere recuperar objetos referenciados.

## Cuando no usar

- Para descargar evidencia real fuera de flujo aprobado.
- Para crear URLs publicas.
- Para reparar manualmente `file_assets` sin audit/plan.

## Permisos requeridos

- Owner approval.
- Provider storage access.
- Entorno aislado para drills.

## Comandos reales

COMMAND NOT AVAILABLE para restore de bucket.

Smoke existente, no restore:

```powershell
python scripts\staging_storage_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id storage_restore_smoke_<timestamp> --confirm-staging --output evidence\slice_runs\storage_restore_smoke_<timestamp>.json
```

## Riesgos

- DB restaurada apunta a objetos faltantes.
- Objetos restaurados pero DB no tiene metadata.
- Signed URLs persistidas en evidencia.
- `storage_path` expuesto.
- Documentos privados descargados fuera de control.

## Criterio de exito

- Bucket/objeto restaurado en entorno aprobado.
- Checksum o size match cuando exista metadata.
- `file_assets` referencia objeto existente.
- Signed URL corta funciona y no se persiste.
- No hay `storage_path` en respuestas publicas/evidence.

## Criterio de aborto

- Provider no confirma backup de storage.
- Mismatch DB/storage.
- Objeto privado expuesto publicamente.
- Secret o signed URL aparece en evidencia.

## Evidencia requerida

- Bucket name.
- Conteos antes/despues.
- Checksums redacted/sinteticos cuando aplique.
- `storage_path_exposed=false`.
- `signed_url_persisted=false`.

## Estado

BLOCKED hasta 31D.
