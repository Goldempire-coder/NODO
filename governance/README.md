# NODO Governance

Esta carpeta controla como se trabaja el proyecto.

La fuente de verdad del producto vive en `../control_plane/`. Esta carpeta no reemplaza el control plane; lo hace operativo para Cursor, Builder y revision del owner.

## Contenido

- `workflow/SLICE_START_PROTOCOL.md`: como iniciar un slice.
- `workflow/CHANGE_CONTROL.md`: como manejar cambios, dudas o contradicciones.
- `workflow/CUT_REVIEW_PROTOCOL.md`: como revisar lineas antes de cerrar.
- `workflow/OWNER_VERIFICATION_PROTOCOL.md`: como Codex/Owner verifica cada slice despues del reporte del Builder.
- `builder_reports/`: reportes producidos por Builder.
- `owner_reviews/`: decisiones y aprobaciones del owner.

## Regla de autoridad

Si hay conflicto:

1. Owner decision escrita gana.
2. `control_plane/00_GOVERNANCE/DECISION_LOG.md` gana sobre documentos viejos.
3. `control_plane/09_SLICES/SLICE_CONTRACTS_MASTER.md` gana sobre interpretaciones del builder.
4. El slice asignado gana sobre trabajo fuera de scope.

Si el conflicto no se puede resolver con esos documentos, el builder debe detenerse.
