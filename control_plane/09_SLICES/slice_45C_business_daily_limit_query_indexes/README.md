# slice_45C_business_daily_limit_query_indexes

Estado contractual: `LOCAL_VALIDATION_IN_PROGRESS`

## Objetivo

Evitar que el calculo del limite diario se vuelva lento cuando existan muchas reservas historicas.

45B corrigio la regla de negocio: los consumos del dia se calculan por `consumed_at`. 45C agrega el indice minimo para que PostgreSQL pueda buscar esos consumos por negocio y ventana UTC sin revisar historial innecesario.

## Que construye

- Migracion reversible `0036_business_daily_limit_query_indexes`.
- Indice parcial para consumos diarios:

```sql
business_capacity_reservations_consumed_daily_idx
```

## Que no construye

- No cambia reglas de negocio.
- No cambia API.
- No cambia UI.
- No ejecuta migraciones.
- No hace deploy.
- No toca pagos, creditos, USDC, Zelle, soporte, intake, reputacion ni bots.

## Riesgo que reduce

Sin indice por `consumed_at`, el marketplace y los snapshots pueden degradarse cuando crezca `business_capacity_reservations` con muchas filas historicas consumidas.

## Validacion esperada

- Prueba estatica de migracion.
- Suite de capacidad.
- Suite API completa.
- `ruff`, `compileall`, build web y secret scan junto al paquete 45B.

## Pendiente antes de staging

Ejecutar `EXPLAIN` en PostgreSQL aislado o staging seguro despues de aplicar la migracion.

