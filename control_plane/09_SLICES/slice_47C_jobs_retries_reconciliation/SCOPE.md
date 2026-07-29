# Slice 47C Scope

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Dentro Del Alcance

- Mapear jobs actuales y sus estados.
- Definir retry, backoff, idempotencia y dedupe.
- Definir jitter, circuit breaker y limite de reintentos para dependencias que
  fallen repetidamente.
- Definir que pasa con job fallido permanentemente.
- Definir heartbeat, edad maxima, backlog y senales de atasco.
- Definir reconciliaciones no destructivas.
- Definir pruebas de doble ejecucion, crash y replay.

## Fuera Del Alcance

- Infraestructura nueva obligatoria.
- Validacion financiera final.
- Borrado de datos.
- Cambios de orden sin contrato.
- Acreditacion manual o automatica nueva sin otro slice.

## Regla AFOS

Un job critico debe poder ejecutarse dos veces sin duplicar dinero, tickets,
notificaciones ni cambios de estado.
