# Cost, Security And Cache Audit - Slice 47H Addendum

Estado: OWNER_REVIEW_REQUIRED
Fecha de incorporacion: 2026-08-05
Documento fuente auditado: SYSTEM_SCREEN_COST_SECURITY_MAP.md

## Veredicto Ejecutivo

El mapa de sistema, pantallas, costos y seguridad es una buena base de
orientacion arquitectonica, pero no demuestra por si solo que NODO sea barato,
seguro o listo para uso real.

La direccion general queda aprobada como orientacion:

- monolito modular antes que microservicios prematuros;
- PostgreSQL como fuente canonica;
- backend como autoridad final;
- frontend estatico, liviano y sin reglas criticas;
- Redis limitado a coordinacion, locks auxiliares y cache efimera;
- archivos privados con carga bajo demanda;
- medicion antes de migrar proveedor o escalar infraestructura.

Estado correcto hasta producir evidencia:

`ARCHITECTURE_DIRECTION_APPROVED - COST_AND_SECURITY_NOT_YET_PROVEN`

## Alcance De Esta Auditoria

Esta auditoria endurece el documento fuente. No inspecciona por si sola el repo,
infraestructura, proveedor cloud, secretos, buckets, logs, indices SQL ni pruebas
de staging.

Usar estas etiquetas:

- `OBSERVED`: aparece explicitamente en documentos o codigo revisado.
- `RECOMMENDED`: direccion razonable, pendiente de evidencia.
- `UNVERIFIED`: falta comprobacion tecnica actual.
- `NOT_TESTED`: falta ejecutar la prueba necesaria.
- `BLOCKING`: no declarar produccion segura hasta resolverlo.

## Resultado Por Area

| Area | Resultado | Evaluacion |
| --- | --- | --- |
| Separacion frontend/backend | Bien orientada | Backend manda en dinero, estados, permisos y ownership. |
| Arquitectura de despliegue | Adecuada para etapa inicial | Monolito modular reduce costo y complejidad operativa. |
| Fuente de verdad | Correcta en intencion | PostgreSQL canonico; faltan pruebas de constraints y transacciones. |
| Cache | Incompleta | Faltan claves, aislamiento, invalidacion y conducta ante fallos. |
| Polling | Riesgo medio-alto | Hay intervalos, pero falta presupuesto por usuario y flujo. |
| Archivos | Parcial | Lazy load esta bien; faltan cuotas, retencion, escaneo y limites. |
| Logs | Buena intencion | Falta masking probado, retencion, muestreo y presupuesto. |
| Acciones criticas | No demostrado | Faltan IDOR, carreras, replay e idempotencia durable. |
| Recuperacion | Bloqueante | No hay RPO, RTO, restore probado ni evidencia fechada. |
| Control financiero infra | Incompleto | No hay presupuesto, alertas ni controles de emergencia. |

## Lo Que Debe Conservarse

### Monolito Modular

Mantener una API, una base PostgreSQL y un frontend web mientras el volumen lo
permita. Separar servicios ahora duplicaria despliegues, secretos, redes,
alertas, logs y trabajo operativo sin aportar seguridad automatica.

### Backend Como Autoridad

El frontend nunca decide:

- saldos o creditos;
- monto, tasa o metodo congelado;
- transiciones de orden;
- ownership;
- permisos administrativos;
- revelacion de datos de pago;
- consumo o devolucion de creditos;
- capacidad final disponible.

Ocultar un boton es UX, no seguridad. Cada accion debe revalidarse en backend
dentro de la misma transaccion que cambia el estado.

### PostgreSQL Canonico

Redis nunca debe ser el unico lugar donde vive una garantia financiera o una
decision de no duplicacion. PostgreSQL debe contener el registro durable, las
constraints y las transacciones que protegen dinero, creditos, estados y
auditoria incluso si Redis se reinicia.

### Archivos Bajo Demanda

No descargar imagenes o evidencias automaticamente ahorra costo, reduce fuga de
datos y mejora rendimiento. Debe combinarse con cuotas, compresion, retencion y
autorizacion por objeto.

## Hallazgos P0

### P0-01 - No Existe Presupuesto Medible

Sin presupuesto mensual y unidad economica no se puede saber si una optimizacion
ahorra dinero o solo mueve el costo.

Definir como minimo:

- costo fijo mensual;
- costo variable por orden completada;
- costo por orden abandonada;
- costo por chat activo por hora;
- costo por ticket de soporte;
- costo por negocio activo;
- almacenamiento nuevo por orden;
- egress por orden;
- margen reservado para picos.

### P0-02 - Idempotencia Durable No Demostrada

Una clave efimera en Redis no basta para acciones financieras. Cada comando
critico debe tener:

- `operation_id` o `idempotency_key` estable;
- actor y scope asociados;
- payload normalizado o hash del comando;
- resultado durable;
- constraint unico en PostgreSQL;
- respuesta repetible ante retry;
- rechazo si la misma clave se reutiliza con payload distinto.

Aplica a creacion, cancelacion, completion, confirmacion de pago, creditos,
compra de creditos y resoluciones admin.

### P0-03 - Locks Sin Segunda Barrera

Un lock Redis reduce carreras, pero no reemplaza:

- constraints de base de datos;
- `SELECT FOR UPDATE`;
- control optimista de version;
- transacciones serializables cuando correspondan.

La seguridad debe sobrevivir a expiracion prematura del lock, pausa de proceso,
failover o reinicio de Redis.

### P0-04 - Cache Sin Contrato De Aislamiento

Toda cache debe definir:

- prefijo de entorno;
- version de schema;
- surface;
- identidad o tenant cuando aplique;
- parametros normalizados;
- version del dato;
- TTL;
- invalidacion.

No debe existir cache compartida para datos privados o autenticados sin una
prueba explicita de aislamiento.

### P0-05 - Recuperacion No Definida

Debe existir una estrategia demostrada de backup y restore:

- RPO: cuanto dato se acepta perder;
- RTO: cuanto puede tardar recuperar;
- backups cifrados y separados del entorno principal;
- restore ensayado en entorno aislado;
- verificacion de conteos, ledgers, archivos y auditoria;
- procedimiento ante corrupcion parcial;
- evidencia fechada del ultimo restore exitoso.

### P0-06 - Seguridad De Archivos Incompleta

Ademas de lazy load y limites de tamano, falta:

- allowlist por MIME y firma magica;
- limites por archivo, mensaje, orden, usuario y dia;
- nombre generado por servidor;
- storage privado;
- autorizacion por objeto antes de firmar URL;
- expiracion corta de URL;
- cuarentena o escaneo para archivos no-imagen;
- eliminacion de EXIF cuando no sea evidencia necesaria;
- retencion y legal hold;
- proteccion contra imagenes de descompresion extrema.

### P0-07 - Prueba IDOR No Demostrada

Cada recurso privado necesita matriz negativa:

- Cliente A no lee ni muta recursos de Cliente B;
- Negocio A no lee ni muta recursos de Negocio B;
- staff sin permiso no accede a evidencia, pagos, soporte o chats;
- surface incorrecta recibe respuesta generica.

Aplica a ordenes, chats, adjuntos, tickets, datos de pago, receiver details,
ratings privados, admin evidence y soporte.

## Estrategia De Costo Minimo Segura

### Principio Rector

Ahorrar eliminando trabajo innecesario, no eliminando controles.

Orden de optimizacion:

1. no hacer la llamada;
2. compartir o deduplicar la llamada;
3. consultar menos filas o columnas;
4. cachear una respuesta segura;
5. procesar por lote;
6. comprimir o reducir el archivo;
7. cambiar infraestructura solo con medicion.

### Unidad Economica

Calcular diariamente y revisar semanalmente:

```text
costo_total_mensual = compute + db + redis + storage + egress
                    + observabilidad + backups + servicios_externos

costo_por_orden_completada = costo_variable_atribuible / ordenes_completadas
costo_por_negocio_activo = costo_total_atribuible / negocios_activos
storage_neto_diario = bytes_subidos - bytes_eliminados_por_retencion
```

Separar costo fijo, variable y crecimiento de datos. No atribuir todo el costo
fijo a una sola orden.

### Gates De Costo

| Gate | Umbral | Accion obligatoria |
| --- | --- | --- |
| Gasto mensual proyectado | 70% del presupuesto | Revisar tendencia y top 3 causantes. |
| Gasto mensual proyectado | 85% | Congelar funciones no esenciales que agreguen consumo. |
| Gasto mensual proyectado | 100% | Activar controles reversibles de emergencia. |
| Crecimiento diario DB | 2x baseline por 3 dias | Investigar tabla, query o flujo. |
| Egress diario | 2x baseline | Revisar adjuntos, bots, crawlers o reintentos. |
| Requests por orden | +25% vs baseline | Bloquear release hasta explicar. |
| Errores o retries | +50% vs baseline | Detener rollout y corregir. |

Los controles de emergencia no pueden borrar evidencia ni alterar balances.
Pueden pausar previews, reducir polling administrativo, impedir uploads no
esenciales o apagar funciones no criticas con feature flags de servidor.

### Presupuesto De Requests Por Flujo

| Flujo | Metrica principal | Gate inicial |
| --- | --- | --- |
| Abrir marketplace | requests y filas leidas | 1 request inicial + paginacion explicita. |
| Ver negocio | requests | 1 request; reutilizar snapshot vigente. |
| Crear orden | mutaciones | 1 comando idempotente; retries no duplican. |
| Abrir chat | requests iniciales | 1 snapshot + deltas posteriores. |
| Chat activo | requests/minuto | politica adaptativa y visible-only. |
| Dashboard negocio | requests iniciales | 1 summary agregado, no N+1. |
| Admin overview | consultas/tiempo | endpoint agregado con rango limitado. |
| Adjuntos | bytes descargados | cero hasta accion explicita o viewport. |

### Polling Adaptativo

El polling debe ser centralizado:

| Estado | Intervalo inicial |
| --- | --- |
| Pantalla oculta o background | pausado |
| Chat visible con actividad reciente | 3-5 s |
| Chat visible sin actividad por 1 min | 10 s |
| Chat visible sin actividad por 5 min | 20-30 s |
| Soporte visible con actividad reciente | 8-10 s |
| Dashboard visible | 30-60 s o refresh por accion |
| Admin background | pausado; attention summary separado |

Controles obligatorios:

- una sola peticion en vuelo por recurso;
- jitter para evitar estampida;
- backoff exponencial ante error;
- cursor incremental o ETag donde sea util;
- cancelar requests al desmontar pantalla;
- refrescar inmediatamente despues de una mutacion propia;
- coalescer consumidores del mismo recurso;
- medir respuestas vacias, bytes y filas, no solo requests.

SSE o WebSocket requiere ADR economico con evidencia. No es mejora automatica.

### Base De Datos

- seleccionar solo columnas necesarias;
- paginar con cursor;
- prohibir listados privados sin limite;
- verificar indices con planes reales;
- evitar N+1 desde summaries;
- materializar snapshots publicos costosos;
- archivar sin romper auditoria;
- usar pool con limites por proceso;
- fijar timeout de statement y transaccion;
- medir slow queries, filas examinadas y locks;
- ejecutar carreras financieras contra PostgreSQL real.

### Storage

- comprimir imagenes del chat cuando el contrato lo permita;
- generar miniaturas una vez;
- usar `Cache-Control: private, no-store` para evidencia sensible;
- lazy load y click-to-load para evidencia admin;
- evitar duplicados por hash dentro del scope correcto;
- aplicar cuotas y retencion por clase de archivo;
- registrar bytes subidos, almacenados y descargados por flujo.

### Observabilidad Economica

No registrar cuerpos privados. Usar metricas agregadas de baja cardinalidad:

- request count por ruta normalizada;
- latencia p50, p95 y p99;
- status code;
- DB time y filas devueltas;
- cache hit/miss por namespace;
- bytes upload/download;
- jobs procesados, fallidos y atrasados;
- retries e idempotency replays;
- costo estimado por flujo;
- logs muestreados para exito y completos para error, sin secretos.

No usar `user_id`, `order_id`, wallet o texto de mensaje como labels de metricas.

## Contrato De Cache Segura

### Reglas Innegociables

1. Cache mejora lectura; nunca es fuente de verdad financiera.
2. Toda key incluye ambiente y version.
3. Datos por usuario, negocio o surface se aislan en la key.
4. No se guardan tokens, PIN, datos de pago completos, signed URLs ni archivos.
5. Toda entrada tiene TTL.
6. La invalidacion ocurre despues del commit exitoso.
7. Un miss consulta la fuente canonica.
8. Un fallo de Redis no duplica dinero ni concede acceso.
9. Logs nunca imprimen valor completo ni key sensible.
10. Un cambio de schema cambia namespace o version.

### Convencion De Keys

```text
nodo:{env}:{schema}:{namespace}:{surface}:{scope}:{query_hash}:{data_version}
```

No incluir PII legible. No reutilizar keys entre staging y produccion.

### Matriz De Cache

| Dato | Cachear | TTL inicial | Scope | Si Redis falla |
| --- | --- | --- | --- | --- |
| Marketplace publico filtrado | Si | 15-30 s | publico + query | consultar DB |
| Detalle publico de negocio | Si | 30-60 s | publico + negocio | consultar DB |
| Snapshot publico reputacion | Si | 1-5 min | publico + negocio | consultar DB |
| Copy/labels publicos | Si | 5-30 min | build/locale | fallback embebido seguro |
| Feature flags no sensibles | Si | 15-60 s | surface/build | default seguro |
| Attention summary | Condicional | 5-10 s | usuario + surface | consultar DB |
| Dashboard negocio | Condicional | 5-15 s | negocio | consultar DB |
| RBAC/permisos | No como autoridad | - | - | negar ante duda |
| Saldos, creditos y ledger | No | - | - | DB o fallar cerrado |
| Capacidad final | No | - | - | transaccion DB |
| Estado de orden para mutar | No | - | - | revalidar en DB |
| Payment instructions | No | - | - | endpoint autorizado |
| Zelle, Pago Movil o wallet completa | No | - | - | endpoint autorizado |
| Signed URLs | No | - | - | generar tras autorizacion |
| Chat privado | No compartida | - | - | DB paginada o delta |
| Soporte/admin privado | No inicialmente | - | - | DB limitada |

### Patron De Lectura

Para lecturas permitidas:

1. construir key normalizada;
2. buscar entrada;
3. responder si existe y es valida;
4. en miss, leer PostgreSQL con limites;
5. guardar respuesta minima con TTL y jitter;
6. devolver;
7. proteger misses simultaneos con single-flight corto.

No guardar errores 5xx. Negative caching solo para recursos publicos realmente
inexistentes, por 3-10 segundos.

### Invalidacion

Preferir versionado por dominio:

- mutacion de anuncio incrementa `market_version`;
- publicacion de reputacion usa `snapshot_version`;
- cambio de attention incrementa version por usuario/surface;
- lector incorpora version en key;
- keys antiguas expiran naturalmente.

La version se incrementa despues del commit o via outbox transaccional. Si DB
confirma y la invalidacion falla, debe existir retry durable.

### Proteccion Contra Estampida

- TTL con jitter 10-20%;
- single-flight por key;
- limite de tamano por valor;
- limite de cardinalidad por namespace;
- queries normalizadas y parametros allowlist;
- el usuario no fabrica keys arbitrarias;
- metricas de hit rate, evictions, memory y hot keys;
- circuit breaker solo para lecturas no criticas;
- limites de conexion y timeout corto.

## Estrategia De Seguridad Compatible Con Bajo Costo

### Acciones Financieras

Cada accion critica debe ejecutarse como comando de dominio:

```text
autenticar -> autorizar -> cargar recurso con lock/version
-> validar transicion -> escribir ledger/evento/estado en transaccion
-> registrar operation_id -> commit -> publicar efectos secundarios
```

Telegram, emails y notificaciones ocurren despues del commit con jobs
idempotentes. Un fallo de notificacion no revierte ni repite dinero.

### Controles Minimos Por Endpoint Privado

- autenticacion valida;
- surface correcta;
- ownership por objeto;
- estado actual leido del backend;
- validacion de input y limites;
- idempotencia para mutaciones;
- rate limit por actor, IP y scope segun riesgo;
- audit event para acciones sensibles;
- respuesta con minimo dato necesario;
- headers de no-cache para informacion privada;
- test negativo de acceso cruzado.

### Rate Limits Por Riesgo

| Riesgo | Ejemplos | Estrategia |
| --- | --- | --- |
| Alto | login, PIN, reveal de pago, compra, confirmacion | limite estricto, cooldown y audit |
| Medio | crear orden, mensaje, upload | limite por actor/recurso y cuotas |
| Bajo | marketplace publico | limite por IP/session y cache segura |
| Staff | investigacion, exportacion, resolucion | RBAC, reason code, audit y limites |

Si Redis cae, endpoints de alto riesgo deben tener proteccion alternativa segura
o fallar temporalmente.

### Privacidad HTTP

- datos privados: `Cache-Control: private, no-store`;
- contenido publico versionado: `public`, `max-age` y ETag definidos;
- nunca mezclar respuestas autenticadas en CDN compartida;
- CORS con origins explicitos;
- CSP, HSTS, content-type strict, referrer policy y frame protection.

### Secretos

- secretos solo en entorno protegido o secret manager;
- rotacion y revocacion documentadas;
- separacion staging/produccion;
- redaccion centralizada antes de logs;
- minimo privilegio para staff;
- ningun secreto en bundle frontend, error trace o analytics.

## Gates De Release

### Gate A - Costo

- baseline de requests por flujo guardado;
- no hay aumento mayor a 25% sin decision aprobada;
- consultas nuevas tienen paginacion y plan revisado;
- bytes de adjuntos respetan cuotas;
- no aparece polling nuevo fuera de la politica central.

### Gate B - Seguridad

- pruebas IDOR por recurso y surface;
- pruebas de replay con misma y distinta carga;
- carreras criticas con PostgreSQL real;
- secretos y PII ausentes de logs;
- URLs privadas expiran y requieren autorizacion;
- rate limits de alto riesgo comprobados.

### Gate C - Resiliencia

- caida de Redis no corrompe saldos ni duplica operaciones;
- retry de job no duplica efecto;
- fallo de Telegram/storage no cambia falsamente estado financiero;
- restore de DB ejecutado y verificado;
- rollback o forward-fix documentado.

### Gate D - Cache

- catalogo de namespaces y owners;
- keys aislan entorno, surface y scope;
- no hay datos prohibidos;
- invalidacion se prueba despues de mutacion;
- staleness maxima aceptable documentada;
- hit rate y memoria observables.

## Plan De Ejecucion

### Fase 0 - Decisiones Del Owner

Definir:

- presupuesto mensual maximo de lanzamiento;
- negocios activos y ordenes por dia esperadas;
- tamano maximo de adjuntos;
- retencion de chat, soporte, evidencia y auditoria;
- RPO y RTO;
- staleness tolerable por lectura;
- funciones que pueden degradarse al superar presupuesto.

Salida: `COST_BUDGET_AND_RETENTION_DECISION.md` aprobado.

### Fase 1 - Instrumentacion Sin Cambiar Reglas

- medir requests, DB time, filas, bytes, cache hit/miss y backlog;
- crear correlation IDs y operation IDs;
- construir dashboard de costo por flujo;
- guardar baseline de staging con escenarios reales.

### Fase 2 - Quick Wins De Bajo Riesgo

- pausar polling oculto;
- coalescer requests duplicados;
- cancelar solapamientos;
- paginar listados;
- lazy load de adjuntos;
- restringir payloads y columnas;
- aplicar compresion y cuotas;
- ajustar logs y retencion.

### Fase 3 - Cache Controlada

- implementar solo marketplace, perfil publico y reputacion publica;
- usar keys versionadas, TTL+jitter y single-flight;
- medir hit rate, staleness, memory y evictions;
- anadir attention summary solo si el beneficio queda demostrado.

### Fase 4 - Endurecimiento Financiero

- idempotencia durable;
- constraints y transacciones;
- locks como optimizacion, no unica defensa;
- outbox para efectos secundarios;
- pruebas de concurrencia y replay.

### Fase 5 - Recuperacion Y Production Gate

- backup cifrado;
- restore aislado;
- verificacion de ledgers y conteos;
- simulacion de caida Redis, storage y Telegram;
- smoke autenticado de Cliente, Negocio y Admin.

## Backlog Priorizado

| Prioridad | Trabajo | Resultado verificable |
| --- | --- | --- |
| P0 | Decidir presupuesto, RPO/RTO y retencion | decisiones firmadas |
| P0 | Idempotencia durable para dinero/creditos | replay no duplica |
| P0 | Constraints y transacciones para carreras | test concurrente pasa |
| P0 | Matriz IDOR por recurso/surface | accesos cruzados negados |
| P0 | Backup y restore real | evidencia de recuperacion |
| P0 | Politica y cuotas de archivos | abuso y costo limitados |
| P0 | Centralizar polling | cero polling oculto o solapado |
| P1 | Baseline de costo por flujo | comparacion por release |
| P1 | Cache publica versionada | hit rate e invalidacion medidos |
| P1 | Outbox para efectos secundarios | retries seguros |
| P1 | Dashboard de costo, errores y backlog | alertas 70/85/100 |
| P1 | Modularizar hotspots de chat/admin/CSS | menor drift con tests |
| P2 | Evaluar SSE/WebSocket con datos | ADR economico |
| P2 | Separar servicios solo por presion medida | ADR con evidencia |

## Criterio Final De Aceptacion

NODO puede avanzar a un gate de uso real solo cuando demuestre:

- cuanto cuesta una orden, un chat y un negocio activo;
- que costo es fijo, variable y acumulado por storage;
- que una caida de Redis no duplica dinero ni concede permisos;
- que ningun usuario accede a recursos de otro;
- que datos privados nunca pasan por cache compartida;
- que polling y adjuntos tienen limites verificables;
- que retries son idempotentes;
- que existe restauracion real dentro del RPO/RTO;
- que un release que aumenta costo o riesgo queda bloqueado automaticamente.

## Decision Required Del Owner

Para transformar esta estrategia en cifras exactas, Carlos debe decidir:

1. presupuesto maximo mensual para lanzamiento;
2. negocios activos esperados en meses 1, 3 y 6;
3. ordenes diarias esperadas en meses 1, 3 y 6;
4. tamano maximo y promedio esperado de cada imagen;
5. retencion requerida para chats, soporte, evidencia y auditoria;
6. tiempo maximo tolerable de caida y perdida de datos.

Estas respuestas no bloquean los P0 tecnicos, pero bloquean declarar una meta
concreta de costos.

## No Tocar En Este Addendum

Este documento no autoriza runtime, migraciones, deploy, produccion, rotacion de
secretos, cambio de proveedor, limpieza de datos ni cambios financieros.
