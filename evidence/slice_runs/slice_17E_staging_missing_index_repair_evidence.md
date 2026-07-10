# Evidence - slice_17E_staging_missing_index_repair

## Scope

Tooling local seguro para aplicar una unica migracion staging aprobada. No se tocaron servicios reales.

## Implementacion

- Se agrego `scripts/apply_staging_single_migration.py`.
- Se agregaron pruebas al archivo existente `apps/api/tests/test_staging_validation_tooling.py`.

## Comportamiento verificado

- Rechaza rutas absolutas, `..`, subdirectorios y archivos que no sean `.up.sql`.
- El dry-run no ejecuta la migracion.
- El apply requiere `--confirm-staging`.
- `0016_query_performance_indexes.up.sql` contiene `orders_active_created_idx`.
- Los 12 statements de `0016_query_performance_indexes.up.sql` son `create index if not exists`.
- El output no contiene secretos.
- El script no referencia ni escribe `nodo_schema_migrations`.

## Validaciones

```text
python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short
26 passed, 1 warning
```

```text
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
164 passed, 1 warning
```

```text
python -m ruff check apps\api scripts
All checks passed!
```

```text
python -m compileall apps\api apps\web\src scripts
OK
```

```text
corepack pnpm --filter @nodo/web build
OK
```

## No real services

- No se ejecuto apply real.
- No se uso DB real.
- No se uso Redis real.
- No se hizo deploy.
- No se imprimieron secretos.

