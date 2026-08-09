# Slice 42D2 Rating Pause Enforcement

Estado: `IMPLEMENTED_LOCAL_VALIDATOR_REVIEW_REQUIRED`

## Objetivo

Aplicar la pausa durable creada por 42D1 en todas las superficies que pueden
publicar un anuncio o crear una orden nueva.

## Guard compartido

La politica backend considera activa la pausa cuando:

```text
database_now < business.ad_publication_paused_until
```

La pausa esta vencida cuando `database_now >= ad_publication_paused_until`.
El guard se aplica a:

- crear/publicar anuncio;
- reactivar anuncio por accion del negocio;
- republicar anuncio;
- search y detalle de marketplace;
- creacion directa de orden.

El bloqueo o suspension Admin conserva precedencia. La pausa no cambia el
estado del anuncio, no mueve creditos ni capacidad y no requiere scheduler.

## Cache y transacciones

- Las consultas PostgreSQL de marketplace filtran la pausa con `now()`.
- Cada cache hit revalida los negocios incluidos contra storage durable; la
  cache nunca autoriza disponibilidad.
- Publicar/reactivar en PostgreSQL vuelve a bloquear y leer el negocio dentro
  de su transaccion antes de tocar creditos o anuncios.
- Crear orden vuelve a leer el negocio con `FOR UPDATE` dentro de la misma
  transaccion que mueve el anuncio y reserva capacidad.
- Si la pausa gana la carrera, responde `AD_NOT_AVAILABLE` sin orden, reserva,
  job ni cambio `active -> in_order`.

## Privacidad

La accion del negocio usa
`BUSINESS_PUBLICATION_TEMPORARILY_UNAVAILABLE` con copy neutral. Marketplace y
creacion de orden usan `AD_NOT_AVAILABLE`. Ninguna respuesta incluye timestamp,
rating, estrellas, cliente, orden origen o causa.

No implementa reporte estructurado, holds, Telegram, soporte, UI nueva ni
cambios de reputacion publica.

No autoriza deploy, staging, produccion ni `READY_FOR_REAL_USE`.
