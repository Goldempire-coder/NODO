# QA.md

## Casos obligatorios

- rating exitoso de orden propia completada;
- rating de orden `admin_resolved` con disputa cerrada;
- rechazo de orden ajena, no completada o con disputa abierta;
- rechazo de actor business/admin;
- rechazo de estrellas fuera de 1..5, tipos no enteros y campos extra;
- replay idempotente, mismatch y duplicado con otra llave;
- carrera deja un solo rating y un solo impacto en agregados;
- detalle de orden expone estado de rating backend-authoritative;
- response y audit no exponen campos internos ni texto libre;
- frontend no calcula reputacion y usa estado propio por orden.

## Comandos

```powershell
python -m pytest apps/api/tests/test_order_ratings.py -q --tb=short
python -m pytest apps/api/tests/test_business_reputation_foundation.py apps/api/tests/test_ads_marketplace.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Ejecutar scan del diff por secretos, campos internos y comentarios de rating.
