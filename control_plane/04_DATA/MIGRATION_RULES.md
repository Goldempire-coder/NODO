# MIGRATION_RULES.md

- Toda migración debe tener nombre, fecha, propósito y rollback cuando aplique.
- No cambiar enum sin actualizar ENUMS_AND_STATUS_MASTER.
- No borrar columnas con datos sin plan de migración.
- Migraciones se prueban local antes de deploy.
