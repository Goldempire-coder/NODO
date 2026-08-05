# Architecture Review Rubric

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Criterio De Puntuacion

Cada categoria se califica de 0 a 10, pero la puntuacion solo vale si incluye
evidencia. La documentacion por si sola no permite 10/10.

| Categoria | Pregunta guia | Evidencia minima | Bloqueador comun |
| --- | --- | --- | --- |
| Comprension del problema | NODO resuelve un problema claramente delimitado? | contrato producto, flujos, fuera de alcance | promesas ambiguas o legales |
| Modelo de dominio | Estados, entidades e invariantes estan claros? | state machine, contratos, pruebas | estados imposibles o transiciones duplicadas |
| Separacion de responsabilidades | Cada modulo tiene una razon de cambio? | mapa de dependencias e imports | UI o repositorio decide reglas de negocio |
| Modelo de datos | La DB impide inconsistencias criticas? | constraints, locks, migraciones, rollback | doble consumo o datos huerfanos |
| Escalabilidad | Se conocen limites por componente? | carga, metricas, umbrales | "autoscaling" sin prueba |
| Control de costos | Se mide costo por flujo y ruido? | consultas, polling, Redis, storage, logs | optimizar sin datos o quitar seguridad |
| Reutilizacion | Lo compartido tiene contrato y propietario? | catalogo de APIs compartidas | utilidades genericas que acoplan dominios |
| Seguridad | Activos y amenazas estan modelados? | threat model, auth, RBAC, IDOR, RLS | secreto o permiso en frontend |
| Concurrencia | Acciones simultaneas tienen ganador unico? | pruebas PostgreSQL, locks, constraints | TOCTOU o updates por id sin estado |
| Idempotencia | Reintentos no duplican efectos? | idempotency keys, dedupe, constraints | doble notificacion, doble cobro, doble cierre |
| Observabilidad | Se puede investigar un incidente? | logs, metricas, version, correlation id | errores sin contexto o sin alerta |
| Manejo de bugs | Hay protocolo de causa raiz? | red test, regression, invariant doc | parche visual sin arreglar backend |
| Recuperacion | Backups/restores estan probados? | restore evidence, RPO/RTO, rollback | backup no restaurado |
| Pruebas | Requisito -> contrato -> codigo -> prueba -> evidencia? | matriz de trazabilidad | solo mocks para transacciones criticas |
| Gobernanza | Los futuros cambios tienen guardrails? | DoD, slice gates, CI checks | builder puede inventar alcance |

## Regla Para 10/10

Solo puede existir 10/10 cuando:

- no hay contradicciones conocidas;
- las decisiones criticas estan cerradas;
- los contratos son verificables;
- las responsabilidades estan delimitadas;
- el modelo de carga es medible;
- los limites de escalabilidad estan identificados;
- los costos tienen escenarios y alertas;
- cada requisito critico tiene prueba;
- cada production gate exige evidencia;
- los riesgos residuales estan documentados.

## Salida Esperada Del Builder

El reporte debe usar esta tabla:

| Categoria | Puntuacion | Evidencia | Bloqueadores | Slices recomendados |
| --- | --- | --- | --- | --- |

Cuando no exista evidencia, usar `UNVERIFIED` o `NOT_TESTED`; no rellenar con
opinion.
