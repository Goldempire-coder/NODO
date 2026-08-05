# Slice 47H - Architecture Foundation Quality Gate

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Adaptar el Prompt Maestro de Arquitectura y Cimientos Escalables a NODO como
un gate preproduccion de auditoria arquitectonica.

Este slice no redisenia NODO desde cero. NODO ya tiene contratos, slices,
runtime, migraciones y decisiones del Owner. El trabajo correcto es comparar el
sistema actual contra los cimientos esperados de un producto operable,
seguro, mantenible, observable, economico y escalable, y producir una lista de
reparaciones gobernadas por slices.

## Problema Que Cubre

La construccion por IA puede dejar un producto que funciona en demos pero se
degrada con el tiempo:

- reglas criticas duplicadas entre frontend, backend y workers;
- controladores, repositorios o pantallas con responsabilidades mezcladas;
- slices que corrigen bugs aislados sin revisar el invariante roto;
- flujos que pasan tests locales pero no tienen evidencia contra PostgreSQL,
  staging, Telegram real o carga representativa;
- documentos que dicen una cosa y runtime que hace otra;
- limites de escalabilidad, costos y observabilidad no medidos;
- gates de produccion basados en "build verde" en vez de evidencia.

## Resultado Esperado

El Builder debe entregar primero un reporte read-only que incluya:

- modelo actual del problema y del dominio de NODO;
- flujos criticos actuales y estados relevantes;
- contradicciones entre documentos, codigo y staging;
- dependencias entre modulos y posibles acoplamientos indebidos;
- responsabilidades mezcladas o duplicadas;
- tabla de cimientos con puntuacion 0-10, evidencia y bloqueadores;
- lista de `DECISION_REQUIRED`, `UNKNOWN_INPUT`, `UNVERIFIED` y `NOT_TESTED`;
- plan de reparaciones por slices pequenos, con pruebas y evidencia requerida;
- recomendacion de que se puede revisar ahora y que debe esperar a datos reales.

## Mapa Operativo

`SYSTEM_SCREEN_COST_SECURITY_MAP.md` contiene el mapa inicial de pantallas,
hooks, APIs, modulos backend, tablas fuente de verdad y estrategia para mantener
NODO seguro y barato sin mover reglas criticas al frontend.

## Auditoria De Costo, Seguridad Y Cache

`COST_SECURITY_CACHE_AUDIT.md` endurece el mapa operativo. Ese documento deja
claro que el mapa es orientacion aprobable, no evidencia de produccion. Antes de
declarar costo bajo, seguridad real o readiness, NODO debe demostrar baseline de
costo, cache aislada, idempotencia durable, segunda barrera en PostgreSQL,
politica de archivos, pruebas IDOR y restore real con RPO/RTO.

## Relacion Con 47G

47G revisa seguridad de lanzamiento: secretos, Telegram Web, Supabase/RLS,
storage, IDOR, headers, dependencias y smoke autenticado.

47H revisa cimientos del sistema completo: problema, dominio, arquitectura,
modulos, datos, carga, costos, observabilidad, recuperacion, pruebas y
gobernanza.

Ambos son gates preproduccion y ninguno declara `READY_FOR_REAL_USE`.

## Regla Madre

Este slice es report-first. No se escribe codigo ni se arreglan bugs durante la
primera respuesta. Si aparece una contradiccion, se detiene y se pide decision
del Owner antes de construir.
