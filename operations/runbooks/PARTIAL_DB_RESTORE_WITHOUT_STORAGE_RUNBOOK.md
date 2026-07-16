# RUNBOOK: Partial DB restore without storage

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

DB restaurada responde, pero documentos/evidencias/adjuntos fallan porque storage no fue restaurado o no coincide.

## Severidad inicial

SEV-1 si afecta payment evidence, credit proofs, audit/evidencia legal-operativa o documentos de negocio.

## Primeros cinco minutos

1. Congelar nuevas cargas de archivos.
2. No eliminar `file_assets`.
3. Medir alcance por conteo, no por descargar documentos reales.
4. Escalar a owner + storage provider.

## Diagnostico

COMMAND NOT AVAILABLE para reconciliacion DB/storage completa hasta 31C/31E.

Checks manuales permitidos solo en entorno aislado:

- Conteo de `file_assets` por `resource_type`.
- Smoke de storage sintetico.
- Muestra aprobada con signed URL corta.

## Recuperacion

- Ejecutar restore storage compatible.
- Luego `POST_RESTORE_INTEGRITY_VALIDATION_SOP.md`.

## Prohibiciones

- No marcar restore completo si storage no coincide.
- No exponer `storage_path`.
- No persistir signed URLs.
