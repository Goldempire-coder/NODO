# Slice 47C - Jobs, Retries And Reconciliation

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Hacer confiables las tareas que corren sin que el usuario toque un boton:
expiraciones, notificaciones, limpieza, pagos/creditos pendientes,
reconciliacion y reintentos.

## Problema Que Cubre

Un sistema real no solo atiende requests HTTP. Tambien necesita tareas de fondo
que puedan fallar, reintentarse, evitar duplicados y dejar evidencia. Si un job
se corta a mitad, NODO debe saberlo y recuperarse sin duplicar efectos.

## Resultado Esperado

- Inventario de jobs actuales y faltantes.
- Politica de idempotencia por job.
- Politica de retry con backoff y limite.
- Dead-letter o estado terminal inspeccionable.
- Politica para controlar el costo del error: circuit breaker, jitter,
  reintentos maximos y no duplicacion de efectos.
- Heartbeat y edad maxima esperada por job critico.
- Profundidad de cola y backlog cuando exista cola.
- Reconciliacion de notificaciones, expiraciones y creditos.
- Alertas hacia 47B cuando un job queda trabado.

## Dependencias

- 10 jobs/notificaciones.
- 19 creditos Base USDC.
- 20B soporte.
- 45A/45B capacidad y limite diario.
- 47A/47B para senales y alertas.

## No Construir Todavia

- No mover dinero automaticamente.
- No validar pagos sin contrato especifico.
- No crear workers 24/7 caros sin decision de infraestructura.
- No borrar datos reales.
- No ejecutar limpieza destructiva.
