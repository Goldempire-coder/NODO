# Slice 42F1 Operational Publication Hold

Estado: `IMPLEMENTED_LOCAL_VALIDATOR_REVIEW_REQUIRED`

## Alcance

Cuando `POST /api/v1/orders/{order_id}/operation-report` crea un reporte
estructurado y `database_now < ad_publication_paused_until`, PostgreSQL crea el
ticket, mensaje, evento y hold en una sola transaccion. Si la pausa ya vencio,
crea solamente el ticket.

El hold durable bloquea crear, publicar, reactivar y republicar anuncios;
tambien excluye search/detail de marketplace y bloquea la creacion directa de
orden. No cambia `ad.status`, ordenes existentes, creditos ni capacidad.

## Liberacion

```text
POST /api/v1/admin/business-publication-holds/{hold_id}/release
```

42F1 autoriza `admin` y `super_admin` activos. Reason e `Idempotency-Key` son
obligatorios. El replay no duplica audit ni cambia el timestamp. Resolver o
cerrar el ticket no libera el hold y liberar uno no afecta otros holds activos.
El detalle Admin del ticket estructurado proyecta el hold necesario para usar
la ruta; Cliente y Negocio no reciben esa proyeccion.

La delegacion Support requiere un mini-slice RBAC posterior: el permiso esta
reservado en contrato, pero el constraint durable actual no lo admite.

## Privacidad

El cliente no recibe si se creo un hold. El negocio no puede ver el ticket ni
el hold. Los errores publicos son neutrales y no incluyen rating, estrellas,
cliente, orden origen, mensaje privado ni causa.

## Fuera de alcance

No implementa Telegram Admin, UI Admin de holds, cambios P2P, chat, pagos,
creditos, capacidad financiera, rating ni reputacion publica. Telegram sigue en
42F2.

No autoriza deploy, staging, produccion ni `READY_FOR_REAL_USE`.
