# slice_40_repo_architecture_cleanup

Estado: `REPO_CLEANUP_IN_PROGRESS_READY_FOR_OWNER_REVIEW`

Fecha: 2026-07-17

## Alcance

Auditoria acotada del repo contra el checklist de app construida con IA lista para produccion, enfocada en:

- orden del repo;
- separacion de responsabilidades;
- exposicion de datos sensibles;
- deuda visible antes de commit/deploy;
- cambios seguros que no alteran reglas de negocio.

## Limpieza aplicada

- Se removieron artefactos locales ignorados: caches Python/pytest/ruff, `tmp/`, `output/` y servidor local temporal de preview.
- Se separo el CSS especifico del panel admin:
  - `apps/web/src/app/admin-web.css`
  - `apps/web/src/app/globals.css`
  - `apps/web/src/app/layout.tsx`

La separacion no cambia reglas, endpoints ni comportamiento de negocio. Solo evita que `globals.css` siga concentrando estilos de superficies distintas.

## Evidencia validada

- `pnpm --filter @nodo/web build`: PASS.
- `git diff --check` sobre los archivos tocados: PASS.
- Los estilos `admin-web*` ya no viven en `globals.css`; quedan en `admin-web.css`.
- `businesses/presenters.py` expone `masked_account` y `holder_name`, no `account_value`, en la lista de metodos de pago.
- Las operaciones de Zelle/USDT en backend mantienen PIN e idempotencia para crear, editar, borrar y disponibilidad.
- Los usos de `eval` encontrados son scripts Lua estaticos de Redis para idempotencia/locks, no ejecucion de entrada del usuario.

## Hallazgos

### HIGH - worktree con multiples slices mezclados

Hay cambios pendientes de varias lineas de trabajo: admin, observabilidad, usuarios, operaciones, notificaciones, mini apps y migraciones. No conviene hacer un commit o deploy unico sin separar por frontera funcional.

Accion recomendada:

- agrupar cambios por slice;
- validar cada grupo;
- commitear por frontera limpia;
- desplegar solo despues de un smoke controlado.

### MEDIUM - `busy` global sigue apareciendo fuera del flujo ya endurecido

El patron aparece todavia en cliente/admin y en algunos flujos compartidos. No todo es bug, pero es una fuente de botones que parecen congelarse si se usa para acciones puntuales.

Accion recomendada:

- convertir acciones sensibles restantes a estados por accion;
- dejar `busy` solo para carga de pantalla o bloqueo global real.

### MEDIUM - scripts de diagnostico grandes

Los scripts de performance/staging son utiles, pero varios ya son grandes y mezclan preparacion, ejecucion, resumen y cleanup.

Accion recomendada:

- moverlos gradualmente a carpetas por dominio, por ejemplo `scripts/staging/`, `scripts/performance/`, `scripts/cleanup/`;
- no hacerlo en el mismo commit que producto.

### MEDIUM - frontera de datos sensibles debe conservarse

El frontend necesita enviar `account_value` al crear/editar Zelle o USDT, pero las listas y pantallas deben operar con `masked_account`. Esta frontera esta bien en la inspeccion actual y debe mantenerse.

Accion recomendada:

- agregar test/scan que falle si `account_value` aparece en respuestas de listado de metodos de pago.

## Que no se cambio

- No se cambiaron reglas financieras.
- No se cambio Base USDC.
- No se cambio Zelle/USDT funcionalmente.
- No se cambio backend de ordenes.
- No se tocaron migraciones.
- No se hizo deploy.
- No se tocaron secretos.
- No se declaro `READY_FOR_REAL_USE`.

## Siguiente slice recomendado

`slice_40A_commit_boundary_and_evidence_pack`

Objetivo:

- separar los cambios actuales por frontera limpia;
- decidir que entra en commit;
- correr pruebas por grupo;
- preparar deploy solo si el candidato queda reproducible.

No hacer:

- no mezclar limpieza con nuevas reglas de producto;
- no desplegar todo el worktree sin agrupar;
- no declarar readiness real sin smoke post-deploy.
