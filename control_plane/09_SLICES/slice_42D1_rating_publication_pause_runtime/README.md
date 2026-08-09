# Slice 42D1 Rating Publication Pause Runtime

Estado: `IMPLEMENTED_LOCAL_VALIDATOR_REVIEW_REQUIRED`

## Objetivo

Persistir una pausa interna de publicacion de 15 minutos cuando el cliente crea
un rating valido de 1 a 5.

## Implementacion

- Migracion `0050_business_ad_publication_pause` agrega
  `businesses.ad_publication_paused_until timestamptz null`.
- Rating y pausa se actualizan bajo el mismo lock/transaccion existente.
- PostgreSQL usa `greatest(existing, now() + interval '15 minutes')`.
- Memory calcula una sola fuente horaria backend y conserva el mayor valor.
- El replay idempotente del mismo rating no ejecuta nuevamente la mutacion.
- Audit interno `business_publication_pause_started` no guarda actor, estrellas,
  comentario, orden, motivo ni datos sensibles.

## Frontera

- Activa: `database_now < ad_publication_paused_until`.
- Vencida: `database_now >= ad_publication_paused_until`.

42D1 solo persiste la frontera. El guard de Ads, marketplace y creacion directa
de orden pertenece a 42D2.

## Privacidad y no efectos

- El campo no se agrega a DTOs publicos o del negocio.
- No crea Telegram, attention, mensaje de chat ni copy visible.
- No cambia anuncios, verification status, risk level, disponibilidad, creditos,
  capacidad, pagos ni reputacion publica.

No autoriza deploy, staging, produccion ni `READY_FOR_REAL_USE`.
