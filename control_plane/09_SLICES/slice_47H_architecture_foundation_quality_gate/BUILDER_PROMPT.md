# Builder Prompt - Slice 47H

Actua como Arquitecto principal de NODO, Auditor de calidad de software,
Especialista en seguridad, Escalabilidad, Bases de datos, Observabilidad,
Confiabilidad y Costos.

Objetivo: adaptar el Prompt Maestro de Arquitectura y Cimientos Escalables a
NODO como auditoria brownfield preproduccion. No estas disenando una app nueva.
Estas revisando si el sistema actual de NODO tiene cimientos suficientes para
seguir a pruebas finales, staging controlado y eventualmente produccion.

## Skills A Usar

- spec-driven-development
- planning-and-task-breakdown
- documentation-and-adrs
- codebase-recon
- code-review-and-quality
- security-and-hardening
- supabase-postgres-best-practices
- observability-and-instrumentation
- performance-optimization
- cost/noise criterio desde 47D
- test-driven-development solo para proponer pruebas, no para implementar en
  la primera respuesta

## Trabajo Inicial Obligatorio

1. Lee este slice completo.
2. Lee:
   - en este slice: `SYSTEM_SCREEN_COST_SECURITY_MAP.md`
   - en este slice: `COST_SECURITY_CACHE_AUDIT.md`
   - `control_plane/00_GOVERNANCE/SOURCE_OF_TRUTH.md`
   - `control_plane/00_GOVERNANCE/DO_NOT_INVENT.md`
   - `control_plane/00_GOVERNANCE/CODE_ARCHITECTURE_MASTER.md`
   - `control_plane/00_GOVERNANCE/ENGINEERING_GUARDRAILS.md`
   - `control_plane/01_PRODUCT/SPEC_MASTER.md`
   - `control_plane/09_SLICES/SLICE_EXECUTION_MATRIX.md`
   - `control_plane/09_SLICES/SLICE_CONTRACTS_MASTER.md`
   - slices 47A-47G
   - contratos activos de ordenes, chat, pagos, reputacion, soporte,
     notificaciones, seguridad, operaciones y estados.
3. No modifiques archivos en la primera respuesta.
4. No escribas codigo.
5. Entrega solo `ARCHITECTURE_FOUNDATION_UNDERSTANDING_REPORT`.

## Reporte Obligatorio

El reporte debe contener:

1. Estado del repo y rama.
2. Documentos leidos.
3. Que entendiste del producto NODO.
4. Problema central que resuelve.
5. Usuarios y roles.
6. Flujos criticos:
   - cliente busca negocio;
   - se crea negociacion;
   - chat;
   - Zelle/USDT;
   - Pago Movil;
   - completion;
   - cancelacion/expiracion;
   - disputa/soporte;
   - rating/reputacion;
   - admin/investigacion.
7. Reglas criticas e invariantes.
8. Riesgos de abuso, perdida, privacidad, reputacion y soporte.
9. Contradicciones encontradas.
10. Supuestos detectados.
11. `DECISION_REQUIRED`.
12. `UNKNOWN_INPUT`.
13. `UNVERIFIED`.
14. `NOT_TESTED`.
15. Mapa de modulos y responsabilidades.
16. Dependencias sospechosas o acoplamientos.
17. Datos criticos y tablas propietarias.
18. Concurrencia e idempotencia critica.
19. Observabilidad y recuperacion.
20. Carga/costos conocidos y faltantes.
21. Cache, polling, archivos y storage:
   - que esta documentado;
   - que esta verificado;
   - que queda como `UNKNOWN_INPUT`, `UNVERIFIED` o `NOT_TESTED`;
   - donde podria filtrarse dato privado o subir costo sin control.
22. Gates P0 de costo, seguridad, resiliencia y cache segun
   `COST_SECURITY_CACHE_AUDIT.md`.
23. Rubrica 0-10 con evidencia y bloqueadores.
24. Plan de reparaciones por slices.
25. Que NO vas a tocar.

## Reglas Duras

- No inventes requisitos.
- No decidas silenciosamente por el Owner.
- No redisenes NODO desde cero.
- No propongas microservicios o Kubernetes sin evidencia.
- No uses frontend como autoridad de reglas criticas.
- No mezcles codigo, migraciones o deploy con esta primera auditoria.
- No declares que algo escala sin carga, limite, metrica y prueba.
- No declares costo bajo sin baseline, presupuesto y unidad economica.
- No uses Redis como unica garantia de dinero, creditos, permisos o estados.
- No cachees datos privados, instrucciones de pago, signed URLs ni chats.
- No ignores backup, restore, RPO o RTO.
- No declares bug corregido sin reproduccion roja y regresion.
- No declares `READY_FOR_REAL_USE`.
- Si hay contradiccion, marca `BLOCKED_BY_CONTRACT_CONFLICT`.
- Si falta decision del Owner, marca `DECISION_REQUIRED`.
- Si falta dato, marca `UNKNOWN_INPUT`.
- Si no verificaste, marca `UNVERIFIED`.
- Si no probaste, marca `NOT_TESTED`.

## Formato Final Del Reporte

Usa este estado:

`INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW`

o, si hay contradiccion bloqueante:

`BLOCKED_BY_CONTRACT_CONFLICT`

No uses `READY_FOR_VALIDATOR_REVIEW` en la primera respuesta porque no hay
implementacion.

## Plan De Reparacion Esperado

Cada reparacion propuesta debe ser pequena y gobernada por slice:

- nombre sugerido;
- problema;
- severidad;
- invariante roto;
- archivos probables;
- pruebas minimas;
- validacion requerida;
- rollback;
- que no debe tocar.

No agrupes todo en un megapatch.

## Backlog P0 Que Debe Considerar

Incluye en el plan, salvo que demuestres que ya existe evidencia suficiente:

- presupuesto y baseline de costo por flujo;
- idempotencia durable en PostgreSQL para comandos financieros;
- segunda barrera PostgreSQL para locks Redis;
- matriz IDOR por recurso/surface;
- politica y cuotas de archivos;
- cache publica versionada y aislada;
- polling centralizado y medido;
- backup y restore real con RPO/RTO;
- release gates que bloqueen aumento de costo, egress, polling o exposicion de
  datos.
