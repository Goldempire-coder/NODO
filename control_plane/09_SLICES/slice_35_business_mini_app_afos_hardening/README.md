# slice_35_business_mini_app_afos_hardening

Estado contractual: `READY_FOR_OWNER_APPROVAL_TO_BUILD_35`

## Objetivo

Convertir la Mini App Negocio en un modulo mas limpio, auditable y operable usando el checklist AFOS recortado al flujo de negocio.

Este slice debe cerrar riesgos pendientes de:

- arquitectura limpia y separacion de responsabilidades;
- acciones sensibles con PIN, auditoria e idempotencia;
- logs y breadcrumbs accionables sin datos sensibles;
- transiciones de pantalla fluidas y medibles;
- evidencia AFOS por control;
- repo organizado para que el siguiente deploy no dependa de memoria de chat.

## Estado de partida

Ya existen avances importantes en los slices 34T-34Z:

- telemetria frontend/backend;
- Home summary separado;
- guards de PIN centralizados;
- split de pantalla de anuncios;
- limpieza de movimientos de creditos;
- UX de compra Base USDC;
- confiabilidad de metodos de cobro.

Este slice no repite esos cambios. Los consolida, prueba y corrige los huecos detectados por la auditoria.

## Resultado permitido

- `READY_FOR_OWNER_REVIEW`
- `BLOCKED_BY_EXPLICIT_EVIDENCE`

## Resultado no permitido

- `READY_FOR_REAL_USE`
- `APPROVED_FOR_PRODUCTION`
- `PRODUCTION_READY`

## Documentos del slice

- `SCOPE.md`
- `DO_NOT_BUILD.md`
- `ARCHITECTURE_CONTRACT.md`
- `DATA_CONTRACT.md`
- `STATE_CONTRACT.md`
- `SECURITY_CONTRACT.md`
- `OBSERVABILITY_CONTRACT.md`
- `AUDIT_EVENTS.md`
- `ERROR_CASES.md`
- `UI_CONTRACT.md`
- `API_CONTRACT.md`
- `QA.md`
- `ACCEPTANCE_CRITERIA.md`
- `BUILDER_PROMPT.md`
