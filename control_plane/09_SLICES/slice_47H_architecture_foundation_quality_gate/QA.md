# Slice 47H QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## QA De La Auditoria

Este slice no valida una feature; valida la calidad del reporte y del plan.

## Checks Obligatorios

- El Builder no modifica archivos en la primera respuesta.
- El Builder declara documentos leidos y fuentes de autoridad.
- El Builder lee `SYSTEM_SCREEN_COST_SECURITY_MAP.md` y
  `COST_SECURITY_CACHE_AUDIT.md`.
- El Builder separa hechos verificados de inferencias.
- Toda contradiccion usa `BLOCKED_BY_CONTRACT_CONFLICT`.
- Toda decision faltante usa `DECISION_REQUIRED`.
- Todo dato de carga/costo ausente usa `UNKNOWN_INPUT`.
- Toda afirmacion sin evidencia actual usa `UNVERIFIED`.
- Toda prueba no ejecutada usa `NOT_TESTED`.
- No hay recomendaciones de microservicios, Kubernetes, proveedor nuevo o
  migracion sin evidencia y decision del Owner.
- No hay afirmaciones de `READY_FOR_REAL_USE`.
- No se proponen reparaciones grandes sin dividir por slices.
- Cada reparacion propuesta tiene:
  - problema;
  - invariante afectado;
  - archivos probables;
  - pruebas minimas;
  - riesgos;
  - rollback;
  - areas que no debe tocar.

## Gates P0 De Costo, Seguridad Y Cache

El reporte no puede afirmar que NODO es barato, seguro o listo para uso real sin
evidencia de:

- presupuesto mensual, costo por flujo y baseline de requests/bytes/filas;
- idempotencia durable en PostgreSQL para comandos financieros;
- locks Redis acompanados por constraints, `FOR UPDATE` o control de version;
- contrato de cache con key, scope, TTL, invalidacion y conducta ante fallo;
- ausencia de datos privados en cache compartida o CDN;
- matriz IDOR negativa por recurso, actor y surface;
- limites y cuotas de archivos por usuario, orden y dia;
- headers `private, no-store` para datos privados;
- backup cifrado y restore ensayado con RPO/RTO;
- release gates que bloqueen aumento injustificado de costo, polling o egress.

## Validacion Documental

Antes de aceptar el slice documental:

- `git diff --check`
- `secret-guard`
- revision de que no se agregaron secretos, comandos con valores sensibles ni
  instrucciones para tocar produccion sin aprobacion.

## Validacion Cuando Se Ejecute El Gate

El Builder debe entregar evidencia, no solo opinion:

- comandos ejecutados;
- resultados de tests/builds/lints;
- comprobaciones SQL si aplica;
- evidencia de staging cuando aplique;
- limitaciones del entorno;
- pruebas que no se pudieron ejecutar y por que;
- riesgos residuales.

## Criterio De Rechazo

Rechazar el reporte si:

- inventa requisitos o cambia decisiones del Owner;
- mezcla 47H con implementacion;
- propone limpiar datos o tocar produccion;
- usa el frontend como autoridad de reglas criticas;
- oculta falta de evidencia;
- recomienda una arquitectura mas costosa sin medicion;
- afirma costo bajo sin baseline o presupuesto;
- usa Redis como unica garantia para dinero, creditos, permisos o estados;
- cachea instrucciones de pago, datos bancarios, signed URLs o chats privados;
- omite backup/restore real;
- omite trazabilidad requisito -> contrato -> codigo -> prueba -> evidencia.
