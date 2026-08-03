# slice_42B_order_ratings

Estado contractual: `BUILD_APPROVED_SLICE_42B`

## Objetivo

Permitir que el cliente propietario califique una sola vez, con 1 a 5 estrellas,
al negocio de una orden completada. El backend crea el rating y recalcula la
reputacion del negocio en la misma operacion segura. El rating individual es
privado: negocio y marketplace reciben una proyeccion estable, sin tier ni
agregados que permitan atribuir un cambio a una calificacion reciente. El orden
del marketplace tampoco usa metricas reputacionales vivas mientras no exista
snapshot publico durable.

## Autoridad

1. `SOURCE_OF_TRUTH.md`
2. `RATING_REPUTATION_MASTER.md`
3. `REPUTATION_CONTRACT.md` del slice 42A
4. `API_CONTRACT.md`, `SECURITY_CONTRACT.md` y `QA.md` de este slice

## Persistencia

La migracion `0033_business_reputation_foundation` ya contiene la tabla
`ratings`, sus FKs, el check 1..5 y el unique por `order_id`. Slice 42B no crea
otra migracion.

## Estado de salida

Solo `READY_FOR_OWNER_REVIEW` o `BLOCKED_BY_EXPLICIT_EVIDENCE`. No autoriza
deploy, produccion ni `READY_FOR_REAL_USE`.
