# QA.md

## Prueba principal

La migracion debe crear un indice parcial para esta forma de consulta:

```sql
where business_id = ?
  and status = 'consumed'
  and consumed_at >= daily_start
  and consumed_at < daily_end
```

## Criterios

- El indice usa `(business_id, consumed_at)`.
- El indice es parcial: `status = 'consumed' and consumed_at is not null`.
- El indice incluye `amount_usd`, `order_id` y `created_at` para reducir lecturas extra.
- El down elimina el indice.
- No se agrega una tabla nueva.
- No se ejecuta la migracion durante el slice local.

## Comandos

```powershell
python -m pytest apps/api/tests/test_business_capacity_matching.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

## Evidencia que falta antes de staging

```txt
EXPLAIN o EXPLAIN ANALYZE sobre PostgreSQL real con historial representativo.
```

