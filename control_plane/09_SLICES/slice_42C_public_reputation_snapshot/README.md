# Slice 42C Public Reputation Snapshot

Estado: `IMPLEMENTED_LOCAL_VALIDATOR_REVIEW_REQUIRED`

## Objetivo

Publicar reputacion agregada sin exponer ratings individuales ni cambios vivos
atribuibles a una operacion. Los agregados internos se calculan de inmediato;
marketplace y negocio leen solo el snapshot durable.

## Reglas

- Menos de cinco ratings elegibles: `Reputacion aun no publicada`.
- Desde cinco ratings: promedio y cantidad se copian cuando el calculo fuente
  tiene al menos 24 horas.
- Una proyeccion publicada puede mostrarse como `4.8 ★ · 12 opiniones`.
  El promedio y el conteo proceden del mismo snapshot durable y nunca
  identifican una orden, cliente o rating individual.
- Un nuevo rating no cambia la proyeccion publica antes de 24 horas.
- El negocio ve la misma proyeccion agregada publicada que los clientes, nunca
  estrellas por orden ni la identidad de quien califico.
- Admin conserva agregados internos exactos.
- Support no recibe ratings individuales.
- El ranking publico permanece por tasa y fecha; no usa metricas vivas ni el
  snapshot en este slice.
- El worker singleton contiene el proceso, pero no se afirma que exista un
  scheduler externo activo hasta validarlo por ambiente.

No autoriza deploy, produccion ni `READY_FOR_REAL_USE`.
