# QA.md

## Casos obligatorios

- rating exitoso de orden propia completada;
- rating de orden `admin_resolved` con disputa cerrada;
- rechazo de `admin_resolved` sin disputa resuelta y de completion reasons
  ausentes, legacy o desconocidos;
- rechazo de orden ajena, no completada o con disputa abierta;
- rechazo de actor business/admin/support;
- rechazo de estrellas fuera de 1..5, tipos no enteros y campos extra;
- replay idempotente, mismatch y duplicado con otra llave;
- carrera deja un solo rating y un solo impacto en agregados;
- detalle de orden expone estado de rating backend-authoritative;
- response y audit no exponen campos internos ni texto libre;
- negocio y marketplace no reciben `rating_avg`, `ratings_count` ni estrellas
  por orden;
- publico y negocio reciben una proyeccion estable que no cambia al crear un
  rating;
- Admin conserva agregados internos exactos, sin rating individual;
- crear un rating no crea mensajes, attention items ni notificaciones Telegram;
- Admin y Support no reciben ratings individuales;
- `sort=trust`, `sort=speed`, `sort=rate` y `sort=null` producen el mismo orden
  por tasa/fecha aunque cambien metricas internas vivas;
- la cache usa un namespace nuevo y la UI no promete confianza o velocidad;
- frontend no calcula reputacion y usa estado propio por orden.
- `confirm-received` conserva el estado `rating` devuelto por backend;
- chat completado ofrece 1..5 estrellas sin navegar a otra pantalla;
- reabrir chat completado carga `rating` desde `GET /orders/{id}`;
- fallo al calificar conserva la seleccion para reintentar.

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
