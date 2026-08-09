# QA

- pausa bloquea crear, reactivar y republicar con error neutral;
- la frontera `database_now >= paused_until` vuelve a permitir la accion;
- bloqueo Admin domina despues del vencimiento;
- Zelle y USDT activos desaparecen de marketplace durante la pausa;
- cache hit revalida contra el negocio durable;
- detalle de anuncio pausado responde `AD_NOT_AVAILABLE`;
- estado del anuncio no cambia por el filtro;
- orden directa falla sin fila, reserva, job, audit de creacion ni cambio de ad;
- PostgreSQL serializa la carrera con el lock durable del negocio;
- DTOs publicos no exponen `ad_publication_paused_until` ni causa;
- 42D1, privacidad de rating y reputacion publica conservan sus regresiones.

Validacion PostgreSQL opt-in:

```powershell
$env:NODO_RUN_RATING_POSTGRES='1'
$env:NODO_RATING_POSTGRES_URL='<localhost disposable nodo_rating_* URL>'
python -m pytest apps/api/tests/test_order_rating_pause_postgres.py apps/api/tests/test_rating_pause_enforcement_postgres.py -q --tb=short
```
