# ENGINEERING_GUARDRAILS.md

Version: 1.0
Status: OFFICIAL
Applies to: Todo el proyecto NODO
Mandatory for: Codex, Cursor, Builder, Reviewer, QA, Auditor y cualquier agente de IA.

## 1. Proposito

Este documento define las reglas oficiales de ingenieria que todo cambio debe cumplir antes de ser aceptado dentro de NODO.

La prioridad de NODO no es escribir codigo rapidamente. La prioridad es construir un producto estable, seguro, escalable, auditable, mantenible y economicamente viable para produccion.

Ningun agente puede ignorar estas reglas. Si un cambio contradice este documento, el cambio queda bloqueado hasta resolver el conflicto con evidencia.

## 2. Autoridad

Este documento es un guardrail transversal. No reemplaza contratos de dominio, seguridad, datos, API, UI o slice; los endurece.

Cuando exista conflicto:

1. `SOURCE_OF_TRUTH.md` define el orden de autoridad.
2. Este documento define el minimo de calidad de ingenieria.
3. El contrato especifico del slice define el scope permitido.
4. Si falta evidencia, no se aprueba.

## 3. Principios fundamentales

Todo cambio debe cumplir:

- No inventar.
- No asumir.
- No ocultar errores.
- No aceptar "funciona en mi maquina" como evidencia suficiente.
- No escribir codigo que no pueda justificarse.
- No optimizar sin evidencia medible.
- No sacrificar arquitectura por velocidad.
- No declarar readiness sin pruebas.
- No mezclar responsabilidades.
- No ampliar scope sin contrato.

La IA acelera el desarrollo. La ingenieria garantiza la calidad.

## 4. Uso de IA y vibe coding

El uso de IA esta permitido solo como acelerador de ingenieria.

La IA nunca reemplaza:

- arquitectura
- auditoria
- validacion
- pruebas
- pensamiento critico
- revision de codigo
- evidencia operativa

Todo codigo generado debe inspeccionarse como si hubiera sido escrito por un desarrollador desconocido.

Nunca se aprueba codigo solo porque compila, porque una pantalla abre o porque un test aislado pasa.

## 5. Definition of Done

Un slice no esta terminado cuando:

- compila
- muestra una pantalla
- pasa un test puntual
- el builder dice `PASS`
- no explota localmente

Un slice solo puede quedar `READY_FOR_OWNER_REVIEW` cuando:

- cumple el contrato aprobado
- no amplia scope
- conserva reglas de negocio
- pasa las auditorias obligatorias aplicables
- genera evidencia cruda revisable
- documenta riesgos residuales
- documenta que NO se toco
- no declara `READY_FOR_REAL_USE`

`READY_FOR_REAL_USE` solo puede autorizarlo el owner.

## 6. Auditorias obligatorias

Todo slice debe evaluar, como minimo:

- Architecture Audit
- Security Audit
- Data/Database Audit
- API Contract Audit
- State Machine Audit
- Race Condition Audit
- Idempotency Audit
- Performance Audit
- Cost Audit
- UX Audit
- Observability Audit
- Dead Code Audit
- Production Readiness Audit
- Red Team Audit

Si una auditoria no aplica, el builder debe explicar por que no aplica.

Si cualquier auditoria encuentra un hallazgo `CRITICAL` o `HIGH`, el slice queda bloqueado.

## 7. Severidad de hallazgos

Severity levels:

- `CRITICAL`: puede exponer secretos, dinero/datos sensibles, romper permisos, duplicar operaciones criticas, corromper estado o tumbar produccion.
- `HIGH`: puede romper un flujo principal, permitir abuso, degradar capacidad de forma grave, inflar costos, o dejar inconsistencias.
- `MEDIUM`: riesgo real pero contenido con workaround o bajo volumen.
- `LOW`: mejora recomendada sin impacto directo inmediato.
- `INFO`: observacion o deuda documentada.

Release gate:

- `CRITICAL` o `HIGH`: bloquea.
- `MEDIUM`: requiere decision explicita del owner o plan de remediacion.
- `LOW` o `INFO`: puede pasar con registro.

## 8. Arquitectura obligatoria

NODO debe mantenerse modular, auditable y separable.

Esta prohibido:

- funciones Frankenstein
- mezclar permisos, validacion, queries, estado, auditoria, storage, notificaciones y response HTTP en una sola funcion
- duplicar logica de dominio
- crear dependencias circulares
- copiar codigo sin motivo
- dejar codigo muerto
- agregar hacks temporales sin ticket/deuda registrada
- poner reglas criticas en el frontend
- convertir pantallas en controladores de negocio
- usar query params como autoridad de seguridad

Responsabilidades esperadas:

- routes: entrada HTTP, dependencias, status codes, schemas
- policies: permisos y ownership
- services/flows: reglas de negocio y transiciones
- repositories: acceso a datos
- storage adapters: archivos privados y signed URLs
- audit: eventos trazables
- idempotency: proteccion contra retries/doble click
- frontend: experiencia, navegacion y feedback, nunca autoridad final

## 9. Backend como autoridad

Toda regla critica vive en backend:

- autorizacion
- ownership
- transiciones de estado
- idempotencia
- calculos monetarios o de creditos
- masking de datos sensibles
- revelacion de payment instructions
- aprobacion/rechazo admin
- acceso a Mini App Negocio
- storage privado

El frontend puede esconder o guiar, pero nunca decidir permisos finales.

## 10. Frontend y superficies

Las superficies oficiales son:

- Mini App Cliente
- Mini App Negocio
- Admin Web Desktop
- Bot Registro Negocios
- Backend unico compartido

Cada superficie debe estar separada por codigo, navegacion, permisos y contratos.

Esta prohibido:

- meter Admin Web dentro de Mini App Cliente
- meter onboarding de negocio dentro de Mini App Cliente
- mezclar handlers cliente/negocio/admin en un mismo modelo
- exponer vistas ocultas como seguridad
- depender solo de `?surface=` para autorizar
- usar copy generico que contradiga NODO

Toda pantalla debe tener:

- loading
- error
- empty state
- retry
- offline/degraded state cuando aplique
- feedback de exito/fallo
- copy seguro
- no overlap visual
- navegacion clara

## 11. Base de datos PostgreSQL/Supabase

Toda modificacion de datos debe minimizar:

- reads innecesarios
- writes innecesarios
- locks largos
- ancho de banda
- storage
- latencia
- fan-out no controlado

Nunca:

- leer tablas completas en runtime usuario
- traer miles de filas sin paginacion/cursor
- crear queries sin indice para filtros frecuentes
- guardar documentos gigantes como JSON sin motivo
- duplicar datos sensibles
- depender de orden implicito sin `order by`
- usar migraciones sin rollback o evidencia
- marcar ledger de migraciones sin reconciliacion fuerte

Cada tabla critica debe tener:

- ownership claro
- indices para queries contratadas
- constraints para invariantes criticas
- timestamps
- audit/evento si cambia estado sensible
- plan de migracion y rollback

## 12. Redis/Upstash y cache

Redis puede usarse para:

- idempotencia
- rate limits
- locks temporales
- cache versionada
- dedupe de jobs/notificaciones

Redis no puede ser la unica fuente de verdad para:

- ordenes
- creditos
- estados finales
- autorizaciones permanentes
- auditoria

Toda cache debe definir:

- TTL
- key shape sin secretos
- invalidacion
- coherencia multi-worker
- comportamiento si Redis falla
- costo esperado
- que datos NO puede contener

## 13. Storage privado

Archivos privados usan storage contratado, actualmente Supabase Storage.

Reglas:

- no exponer `storage_path`
- no guardar signed URLs persistidas
- signed URLs deben ser cortas y autorizadas
- MIME y size limit deben estar contratados
- cada archivo debe vincularse por `file_assets`
- logs y responses no deben incluir secretos ni rutas internas

## 14. Telegram, bots y webhooks

Telegram no es autoridad de negocio; identifica al usuario y transporta eventos.

Reglas:

- validar `initData` en backend
- separar bot cliente y bot de intake por token y webhook
- no imprimir tokens ni webhook secrets
- procesar updates idempotentemente
- no crear negocios activos desde el bot intake
- no dar acceso a Mini App Negocio desde el bot
- no confiar en texto del usuario para permisos
- todo webhook debe tener secret y tests

## 15. Seguridad

Nunca confiar en el cliente.

Nunca exponer:

- API keys privadas
- service role keys
- JWT secrets
- refresh tokens
- bot tokens
- storage paths
- account values completos
- documentos privados
- stack traces
- SQL o params sensibles

Todo endpoint sensible debe validar:

- autenticacion
- rol
- ownership
- estado permitido
- idempotencia si muta
- rate limit
- audit log si cambia estado/datos sensibles

## 16. Ingenieria defensiva

Antes de aprobar cualquier cambio, responder:

- Que pasa si el usuario toca dos veces?
- Que pasa si se pierde internet?
- Que pasa si cambia de dispositivo?
- Que pasa si cierra Telegram?
- Que pasa si llega el mismo request dos veces?
- Que pasa si Redis falla?
- Que pasa si Postgres tarda?
- Que pasa si storage falla?
- Que pasa si Telegram reintenta el webhook?
- Que pasa si dos usuarios intentan la misma accion?
- Que pasa si un admin repite approve/reject?

Si la respuesta no esta implementada o documentada, el slice no esta listo.

## 17. Race conditions e idempotencia

Operaciones criticas deben ser seguras contra:

- doble click
- retry del cliente
- retry de webhook
- requests paralelos
- race sobre el mismo anuncio
- doble reporte
- doble confirmacion
- doble consumo de creditos
- doble acreditacion
- doble resolucion

Mecanismos aceptables:

- `Idempotency-Key`
- unique constraints
- locks transitorios
- transacciones atomicas
- state checks en SQL
- ledger append-only
- tests de concurrencia

No puede existir ninguna operacion critica que dependa solo de "el usuario no lo hara dos veces".

## 18. Offline y degradacion

Toda funcionalidad debe definir:

- que pasa sin internet
- que pasa al recuperar conexion
- como se evitan duplicados
- como se muestran errores
- que acciones se bloquean
- que informacion queda visible

NODO no debe fingir exito si no hubo confirmacion backend.

## 19. Performance

Cada flujo principal debe medir:

- tiempo de carga
- tiempo hasta interaccion
- p50, p95, p99
- errores
- timeouts
- queries
- cache hit/miss
- pool saturation
- Redis latency
- DB acquire wait
- CPU/memoria cuando aplique

Todo cuello de botella debe documentarse con evidencia.

No se acepta "parece lento" ni "parece rapido" como conclusion final.

## 20. Cost engineering

Todo cambio debe responder:

- Cuantos requests nuevos genera?
- Cuantos reads DB?
- Cuantos writes DB?
- Cuantos hits Redis?
- Cuanto storage?
- Cuanto ancho de banda?
- Cuantas llamadas a servicios externos?
- Cuanto cuesta con 100, 1,000, 10,000, 100,000 y 1,000,000 usuarios?
- Puede una accion costar mas que el ingreso esperado?

Para NODO, el costo por operacion debe mantenerse proporcional al modelo de negocio. Un anuncio de bajo valor no puede disparar una cadena de infraestructura cara por cada lectura.

Si el costo crece de forma innecesaria, el diseno debe cambiar antes de aprobar.

## 21. Escalabilidad

Todo modulo debe declarar:

- limite conocido actual
- cuello probable
- plan de evolucion
- metricas para decidir el siguiente escalon
- costo del siguiente escalon

No se declara capacidad 10,000, 100,000 o 1,000,000 sin prueba o modelo tecnico defendible.

Escalar no significa solo aumentar servidor. Tambien implica:

- menos round trips
- menos DB reads
- cache correcta
- queries con indices
- paginacion
- workers controlados
- pool budgeting
- colas donde aplique
- medicion real en staging

## 22. Observabilidad

Todo flujo critico debe generar evidencia suficiente para auditoria.

Se debe registrar solo lo necesario para:

- diagnostico
- trazabilidad
- investigacion
- auditoria

Nunca registrar informacion sensible.

Cada evento critico debe incluir:

- actor
- recurso
- accion
- resultado
- request id/correlation id cuando aplique
- timestamp
- razon admin si aplica

## 23. Red Team

Antes de aprobar un release, debe intentarse romper el sistema.

El auditor debe intentar:

- duplicar ordenes
- duplicar creditos
- duplicar reportes
- duplicar webhooks
- leer datos ajenos
- escalar privilegios
- saltar surface/session
- usar un Telegram ID no vinculado
- forzar estados invalidos
- abusar de latencia
- abusar de reintentos
- abusar de concurrencia
- subir archivos invalidos
- exponer storage paths

El objetivo es encontrar fallos antes que el usuario.

## 24. Release gate

Un release queda bloqueado si existe:

- cualquier `CRITICAL`
- cualquier `HIGH`
- migracion staging sin evidencia
- rollback no probado
- secreto expuesto
- endpoint admin sin RBAC
- storage privado exponiendo rutas
- estado inventado
- doble operacion critica posible
- error 500 reproducible en flujo principal
- performance/costo sin medir en flujo afectado

No hay excepciones automaticas.

## 25. Responsabilidades de Codex/Builder/Reviewer

Codex y Builder no actuan solo como generadores de codigo.

Durante el ciclo deben asumir sucesivamente:

- Planner
- Builder
- Reviewer
- Architecture Auditor
- Security Engineer
- Performance Engineer
- Cost Engineer
- Database Engineer
- QA Engineer
- Red Team
- CTO

Cada rol debe intentar encontrar errores introducidos por el anterior.

## 26. Evidencia minima por slice

Todo `BUILDER_REPORT` debe incluir:

- scope autorizado
- archivos modificados
- funciones modificadas
- contratos cumplidos
- tests ejecutados
- resultados crudos
- stress/smoke si aplica
- scans de secretos/datos privados
- riesgos residuales
- que NO se toco
- estado final tecnico

Sin evidencia, no hay aprobacion.

## 27. Checklist obligatorio

Antes de aceptar un slice:

- Arquitectura revisada.
- Seguridad revisada.
- Datos y migraciones revisados.
- API contract revisado.
- State machine consistente.
- Idempotencia revisada.
- Race conditions probadas.
- Performance medida.
- Costos estimados o medidos.
- Offline/degradacion definido.
- UX validada.
- Codigo muerto eliminado.
- Observabilidad implementada.
- Red Team ejecutado o justificado.
- Production audit revisado.
- Evidencia generada.
- Documentacion actualizada.

Si cualquiera de estos puntos falla, el slice no puede considerarse terminado.

## 28. Regla final

La velocidad nunca tiene prioridad sobre la calidad.

Todo cambio debe ser:

- correcto
- auditable
- escalable
- seguro
- mantenible
- reproducible
- economicamente defendible
- listo para operar en produccion cuando el owner lo autorice

Si existe duda razonable sobre la calidad de un cambio, el cambio se rechaza hasta contar con evidencia suficiente para aprobarlo.

## 29. Delegacion interna

La delegacion a empleados/colaboradores debe ser granular, revocable y auditable.

- No usar solo `users.role` para permisos finos.
- No conceder permisos criticos por frontend.
- No mezclar soporte operativo con disputa formal.
- No dar a staff delegado acciones de dinero, creditos, usuarios, access links, ordenes, anuncios o resolucion de disputas salvo contrato futuro explicito.
- La revocacion/suspension staff debe cortar capacidades inmediatamente.
