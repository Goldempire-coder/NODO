# QA

- estrellas 1, 2, 3, 4 y 5 crean pausa de 15 minutos;
- replay con la misma llave conserva el timestamp;
- segundo rating distinto conserva el mayor timestamp;
- concurrencia Memory no pierde la pausa;
- concurrencia PostgreSQL conserva `greatest`;
- rating invalido, actor ajeno y orden no completada no crean pausa;
- evento audit neutral se crea una sola vez;
- response de rating y DTOs publicos no exponen campo ni causa;
- migracion `0050` aplica y revierte en PostgreSQL desechable;
- datos existentes sobreviven al ciclo down/up;
- regresiones de privacidad y reputacion siguen pasando.

Validacion minima:

```powershell
python -m pytest apps/api/tests/test_order_ratings.py -q --tb=short
python -m pytest apps/api/tests/test_order_rating_pause_postgres.py -q --tb=short
python -m ruff check apps/api scripts
python -m compileall apps/api
git diff --check
```

La prueba PostgreSQL requiere opt-in y una base localhost desechable cuyo nombre
empiece por `nodo_rating_`.
