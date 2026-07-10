# ACCEPTANCE_CRITERIA.md

## Estado esperado

`READY_FOR_OWNER_REVIEW` solo si:

- Admin Web es superficie separada.
- No vive en Mini App Cliente ni Mini App Negocio.
- Tiene layout desktop-first.
- Usa sidebar/top bar/tablas/filtros/detalle.
- Reutiliza endpoints admin existentes.
- No inventa reglas de negocio.
- No cambia reglas de creditos, ordenes, disputas o anuncios.
- No expone datos sensibles.
- Tests y scans pasan o reportan bloqueo exacto.

## No aceptable

- Admin dentro de Mini App Cliente.
- Admin dentro de Mini App Negocio.
- Telegram MainButton como navegacion primaria.
- Bottom nav Telegram.
- UI generica o landing.
- Mutaciones admin sin reason/audit/idempotencia.
- `READY_FOR_REAL_USE`.
