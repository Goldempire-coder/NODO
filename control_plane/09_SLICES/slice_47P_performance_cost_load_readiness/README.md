# Slice 47P - Performance, Cost & Load Readiness Mapping

Estado: `INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW`

Fecha de inspeccion: 2026-08-05

Este documento es un mapa tecnico y un plan de medicion. No cambia producto,
no agrega cache, no agrega indices y no declara readiness de produccion.

Actualizacion 47P0/47P0.1: `BASELINE_47P0.md` contiene la evidencia posterior
contra PostgreSQL/Redis locales. El baseline cerro los gaps de
`private, no-store`, confirmo las carreras principales y 47P0.1 reconcilio el
formato local de telefono de Pago Movil entre runtime y PostgreSQL mediante la
migracion reversible 0048. Esto es evidencia local, no readiness de produccion.

## 1. Autoridad Y Metodo

Se preserva el flujo P2P chat-first vigente. PostgreSQL sigue siendo la fuente
canonica y el backend sigue siendo autoridad para estados, ownership, capacidad,
creditos, pagos e idempotencia de negocio.

Skills aplicados:

- `planning-and-task-breakdown`: separacion en 47P0-47P5 y gate final.
- `performance-optimization`: medicion antes de optimizar; separacion de tiempo
  de backend, DB, Redis y transporte.
- `observability-and-instrumentation`: inventario de request IDs, tiempos,
  perfiles, jobs y huecos de metricas.
- `shipping-and-launch`: distincion entre evidencia local, staging, product-gate
  y readiness de produccion.
- `security-and-hardening`: clasificacion de datos cacheables/prohibidos,
  cardinalidad de metricas y pruebas sin datos reales.
- `supabase-postgres-best-practices`: revision de pooling, transacciones,
  consultas, indices y candidatos que requieren `EXPLAIN` real.
- `test-driven-development` y `pytest-skill`: escenarios repetibles con
  invariantes antes de cambios de rendimiento.
- `playwright` / `webapp-testing`: evaluado para smoke movil; no ejecutado porque
  no existe harness Playwright instalado y este slice no autoriza un smoke
  autenticado de staging.

Etiquetas usadas:

- `OBSERVED`: confirmado en codigo, configuracion o evidencia revisada.
- `HISTORICAL`: evidencia anterior que no prueba el HEAD actual.
- `UNVERIFIED`: falta evidencia del entorno actual.
- `NOT_TESTED`: prueba no ejecutada en este slice.
- `OWNER_DECISION_REQUIRED`: requiere presupuesto, SLO o autorizacion.

## 2. Repo Inspeccionado

| Campo | Resultado |
| --- | --- |
| Repo | `C:\Users\carlo\Documents\Playground\NODO` |
| Rama | `codex/intake-admin-review-v2` |
| HEAD local | `1828a5cf0882f5617df895ecb3bbfbdf3e06ba64` |
| Worktree inicial | Sucio: 68 archivos tracked modificados y 10 entradas untracked antes de 47P |
| `git diff --check` inicial | Exit 0; solo warnings CRLF en cambios preexistentes |
| Archivo creado por 47P | Este `README.md` |

Los cambios preexistentes no se limpiaron, revirtieron ni atribuyeron a 47P.

## 3. Alcance Inspeccionado

### Backend E Infra Local

- `apps/api/app/main.py` y `apps/api/app/core/config.py`.
- pooling en `apps/api/app/shared/db/connection.py`.
- cache, rate limit, idempotencia, storage y observabilidad compartidos.
- ads/marketplace, ordenes, capacidad, chat, soporte, notificaciones, jobs,
  creditos y archivos.
- migraciones e indices hasta `0045`.
- `Dockerfile`, `docker-compose.local.yml`, `railway.json` y scripts locales.

### Frontend

- polling Cliente, Negocio y Admin.
- API clients de marketplace, ordenes, chat, soporte, notificaciones y datos
  sensibles.
- politicas de cache de Cloudflare/Next export.
- build de produccion y tamano inicial de rutas.

### No Inspeccionado O No Probado

- `UNVERIFIED`: configuracion real de `max_connections`, CPU, memoria, disco,
  replicas, autoscaling y pooling del PostgreSQL/Supabase de staging.
- `UNVERIFIED`: consumo y plan actual de Redis/Upstash.
- `UNVERIFIED`: dashboard Railway, logs centralizados y alertas del proveedor.
- `UNVERIFIED`: scheduler externo de expiracion/escalacion de ordenes.
- `NOT_TESTED`: `EXPLAIN (ANALYZE, BUFFERS)` con cardinalidad representativa.
- `NOT_TESTED`: carreras PostgreSQL reales del HEAD actual.
- `NOT_TESTED`: Redis bajo carga o durante degradacion.
- `NOT_TESTED`: smoke autenticado Cliente/Negocio/Admin en staging.
- `NOT_TESTED`: teclado/chat movil en navegador real durante este slice.
- `NOT_TESTED`: carga de archivos; deliberadamente excluida para no generar
  costo ni presion de memoria sin un plan aprobado.

## 4. Resumen Ejecutivo

NODO ya tiene mejores bases de las que tendria un sistema sin preparacion:

- PostgreSQL canonico con transacciones y locks en operaciones criticas.
- Redis para coordinacion, idempotencia, rate limits, jobs y cache efimera.
- pooling acotado, request/correlation/operation IDs y tiempos de backend.
- indices para ordenes, mensajes, soporte, jobs y capacidad.
- cache versionado de marketplace con TTL corto e invalidacion.
- harness Python local y guardrails de staging ya existentes.
- frontend estatico servido con assets inmutables.

Eso no demuestra todavia capacidad para 10, 50, 100 o 250 usuarios del flujo
completo. El riesgo principal no es una unica query conocida, sino la suma de
polling, consultas compuestas de attention, limites del pool, workers en el mismo
proceso y evidencia historica que ya no representa el runtime actual.

No se recomienda agregar cache o indices antes de ejecutar 47P0-47P3.

## 5. Hallazgos Por Severidad

### Critical

No se confirmo un defecto critico nuevo en esta inspeccion. Esto no equivale a
ausencia de defectos: las carreras PostgreSQL reales y el flujo autenticado
siguen `NOT_TESTED` para el HEAD actual.

### High

| Hallazgo | Evidencia | Impacto | Accion recomendada |
| --- | --- | --- | --- |
| No existe baseline vigente del flujo completo | La evidencia de carga encontrada es de julio y staging corre un SHA distinto al HEAD local | No se puede afirmar soporte para 10/50/100/250 usuarios actuales | 47P0 y 47P1 con dataset y SHA fechados |
| Los harness locales principales quedaron desalineados del flujo vigente | `scripts/local_smoke.py` revela instrucciones antes del share de negocio y marca entrega sin Pago Movil estructurado; `scripts/concurrency_local.py` crea muchos anuncios Zelle para un negocio | Un PASS puede medir un flujo legacy o fallar por reglas nuevas, no por capacidad | Reconciliar fixtures y pasos en 47P0 sin cambiar runtime |
| Polling de soporte puede solaparse y sigue activo oculto | `ClientSupportScreen.tsx` cada 8 s; `BusinessSupportScreen.tsx` cada 5 s; sin visibility check ni in-flight guard | Multiplica HTTP/DB, especialmente si list + detail tardan mas que el intervalo | 47P2: medir y luego visible-only, no overlap, backoff y jitter |
| Admin hace polling global sin visibility guard | `useAdminWebModel.ts`: dashboard + notificaciones cada 15 s; soporte cada 5 s en esa vista | Costo constante por operador y requests solapados en degradacion | 47P2 con presupuesto por vista |
| Expiracion/escalacion no tiene ejecucion automatica demostrada | Existe `jobs/scheduler.py` y worker, pero el lifespan solo arranca sender de notificaciones y watcher USDC | Ordenes vencidas pueden acumularse si no existe scheduler externo | 47P4/47P5: evidencia de ultima ejecucion, lag y alerta |
| Respuestas privadas de chat/soporte no declaran siempre `private, no-store` | El GET general de mensajes y rutas de soporte no aparecen entre las rutas que fijan ese header | Riesgo de cache local/intermediario y datos stale | Slice de seguridad separado; no arreglar dentro de 47P sin contrato |

### Medium

| Hallazgo | Evidencia | Impacto | Accion recomendada |
| --- | --- | --- | --- |
| `attention-summary` es una consulta compuesta frecuente | Hasta 50 ordenes + 50 tickets, ultimos mensajes y acknowledgements cada 15 s | Puede convertirse en hot path de DB antes que marketplace | EXPLAIN y conteo de queries en 47P3; no cachear sin aislamiento probado |
| Indices de attention no siguen su orden real | Query ordena por `updated_at, id`; indices de ordenes principales usan `created_at` | Sort/scan creciente con historial | EXPLAIN antes de proponer indice compuesto |
| Marketplace agrega capacidad con lateral por negocio | `ads/postgres_repository.py` suma reservas abiertas y consumo diario dentro de la busqueda | Costo crece con negocios/reservas candidatas | EXPLAIN a 10/100/1000 negocios y cold/warm cache |
| Cursor de marketplace no representa todo el sort | Orden SQL por tasa + fecha, cursor solo por fecha | Riesgo de duplicados/saltos y trabajo repetido | Contrato de cursor compuesto en slice separado |
| Pool y thread limit pueden crear cola interna | Pool default 20, timeout 10 s; thread limit 40; un worker por defecto | A c50 puede haber espera aun con DB sana | Medir `db:acquire`, saturacion y conexiones por replica |
| Marketplace rate limit es in-memory en runtime | `main.py` usa `InMemoryRateLimiter` solo para marketplace | Limite se multiplica por replicas y reinicios | Medir abuso; decidir rate limit distribuido sin bloquear lecturas legitimas |
| Redis degradado tiene semanticas distintas | Rate limit cae a memoria; cache cae a DB; idempotencia Redis no tiene fallback | Puede aumentar carga o bloquear mutaciones | Pruebas de degradacion controlada en 47P1/47P4 |
| Uploads se leen completos en memoria | Limite de 5 MiB en chat, soporte, evidencias y creditos | 100 uploads simultaneos pueden presionar cientos de MiB | No incluir archivos en S1-S3; medir flujo separado con limites bajos |
| Observabilidad no expone salud de recursos | Hay logs y tiempos, pero no gauges de pool, queue lag, Redis commands, CPU/memoria ni DB time global | Se sabria que algo esta lento, no necesariamente por que | 47P4 con metricas de baja cardinalidad |

### Low

- El frontend no tiene un presupuesto de bundle automatizado. El build actual es
  razonable para una primera medicion, pero puede crecer sin gate.
- No hay Playwright instalado como dependencia directa. Hay evidencia historica
  de screenshots, pero no un smoke movil repetible del HEAD actual.
- `/health`, `/ready` y `/version` son utiles para diagnostico, pero no deben
  usarse como sustituto de un flujo autenticado.

## 6. Configuracion Runtime Observada

| Area | Configuracion observada | Riesgo / lectura |
| --- | --- | --- |
| API | Uvicorn, `WEB_CONCURRENCY=1` por defecto | Una replica/proceso requiere medicion antes de escalar workers |
| Threadpool | `API_THREAD_LIMIT=40` | Puede admitir mas trabajo que las 20 conexiones DB disponibles |
| DB pool | Max 20 por proceso, timeout 10 s, warm default 8 | Multiplica conexiones por worker y replica |
| PostgreSQL | Repositorios productivos usan psycopg y transacciones | Canonico; falta max connections y EXPLAIN real |
| Redis | Rate limits, idempotencia, cache, locks de jobs | Disponibilidad/costo por comando no medidos |
| Marketplace cache | Layered local + Redis, TTL 30 s, version cache 1 s, shared-hit local 5 s | Buen candidato; invalidacion y stampede multi-replica deben medirse |
| Admin read cache | In-memory, TTL 5 s | Reduce lecturas por proceso, no comparte entre replicas |
| Auth user cache | In-memory, TTL 2 s | Polling de 5-15 s probablemente vuelve a consultar autoridad |
| Notification sender | Loop interno, 10 s, batch 50 | Comparte proceso/threadpool; usa dedupe/locks |
| USDC watcher | Loop interno condicional, 30 s, batch 50 | Puede generar RPC/costo; excluir de carga salvo simulador local |
| Expiration worker | Implementado con lock y job runs | Ejecucion automatica externa `UNVERIFIED` |

## 7. Mapa De Flujos Criticos

| Flujo | Endpoints principales | Protecciones observadas | Costo probable | Evidencia pendiente |
| --- | --- | --- | --- | --- |
| Marketplace | `GET /api/v1/ads/search`, `GET /api/v1/ads/{id}` | Auth, rate limit, filtro server-side, cache 30 s | Joins + aggregate lateral de capacidad | Cold/warm p95, EXPLAIN, cardinalidad |
| Crear orden | `POST /api/v1/orders` | Idempotency-Key, lock/transaccion, revalidacion de anuncio/capacidad/limite | DB locks, eventos, audit, cache invalidation, job | Carrera real PostgreSQL del HEAD |
| Cancelar/no atender/expirar | cancel cliente, cannot-attend negocio, expiration worker | Estado previo condicional, liberacion idempotente, eventos | Locks de orden/anuncio/capacidad, notificacion | Pago vs cancel/expire real |
| Chat | GET/POST mensajes, attachments, share payment details | Ownership, rate limit, idempotencia, cursor max 50 | Polling 5 s, mensajes + attachments | 50 chats distintos y hot thread |
| Reportar pago | payment instructions/evidence/report | Ownership, estado, monto, unicidad hash/proof, transaccion | Storage opcional + DB + audit + notify | Pago vs cancel/expire y Redis failure |
| Confirmar pago negocio | `confirm-payment` | Estado y actor, transaccion, consumo de credito una vez | DB locks + ledger + notification | Replay y race real |
| Pago Movil | PUT/GET receiver-details | Estructurado, ownership, reveal auditado, no-store | Lectura/escritura sensible | Concurrencia reveal/update y cache headers |
| Entrega/completion | mark-delivered, confirm-received | Estado condicional, disputa bloquea, capacidad una vez | DB + audit + jobs/notificaciones | delivered vs disputed/completed |
| Rating | POST rating + GET order | Completed/owner/unique, agregado interno y snapshot publico | Recalculo y snapshot | Volumen y contention por negocio |
| Attention | GET summary + POST acknowledge | Scope por surface, proyeccion segura, no-store | Varias queries por poll cada 15 s | Query count, EXPLAIN, p95 |
| Soporte | list/detail/message/attachment/status | Scope, idempotencia, max 50, archivos privados | Polling 5/8 s, list + detail | No-overlap y volumen de tickets |
| Jobs/Telegram | notification sender, expiration/escalation | Dedupe DB, retry, locks Redis, job runs | Redis + DB + Telegram | Queue lag, retry storm, scheduler evidence |
| USDC credit purchase | create/submit/watcher/admin | Idempotencia, verifier, audit | RPC externo y polling watcher | Solo simulador local en 47P; no pagos reales |

## 8. Polling Y Presupuesto Actual

Los numeros siguientes son maximos aproximados por usuario con la vista montada,
sin contar retries de auth ni acciones manuales.

| Superficie | Poll | Protecciones | Requests aproximados |
| --- | --- | --- | --- |
| Cliente chat | 5 s | Visible-only, no overlap, pausa durante send/upload | 12 GET/min; chat completed puede llegar a 24 HTTP/min por hydration adicional de rating |
| Negocio chat | 5 s | Visible-only, no overlap, pausa durante send/upload | 12 GET/min |
| Attention Cliente/Negocio | 15 s | Visible-only, in-flight guard, jitter, backoff 15-120 s | 4 HTTP/min, pero cada llamada compone varias queries DB |
| Cliente soporte | 8 s | Solo mientras pantalla esta montada; sin visibility/in-flight/backoff | 7.5 list/min; hasta 15 HTTP/min con detalle seleccionado |
| Negocio soporte | 5 s | Solo mientras pantalla esta montada; sin visibility/in-flight/backoff | 12 list/min; hasta 24 HTTP/min con detalle seleccionado |
| Admin global | 15 s | Sin visibility/in-flight/backoff observado | 4 dashboard + 4 notification count/list por minuto |
| Admin soporte | 5 s | Solo vista soporte; sin visibility/in-flight/backoff observado | Hasta 24 HTTP/min adicionales con detalle |

Riesgo: `setInterval` puede iniciar otro refresh antes de terminar el anterior.
Con latencia degradada, el costo deja de ser lineal y aparecen colas en navegador,
threadpool y pool DB.

## 9. Queries E Indices A Medir

No se propone ningun indice en este slice. Cada candidato requiere SQL real,
cardinalidad y `EXPLAIN (ANALYZE, BUFFERS)` en PostgreSQL desechable.

| Query | Indices actuales relevantes | Evaluacion |
| --- | --- | --- |
| Marketplace por metodo/monto/tasa | `ads_marketplace_active_idx`, business/payment method joins | Buen punto de partida; el lateral de reservas y filtros de negocio requieren EXPLAIN |
| Attention negocio/remitter por `updated_at desc, id desc` | `orders_business_status_created_idx`, `orders_remitter_status_created_idx` usan `created_at` | Mismatch claro; candidato a indice compuesto solo si EXPLAIN confirma costo |
| Mensajes por orden | `messages_order_created_idx(order_id, created_at)` | Soporta rango; query tambien ordena por `id`, revisar ties y heap fetches |
| Ultimo mensaje por hasta 50 ordenes | Mismo indice, con filtros de visibility/status/sender | `distinct on` puede ser aceptable a 50; medir con hilos grandes |
| Support list/detail | requester/business/status/updated y ticket/message indexes | Mejor alineado; medir filtros admin y cursor con timestamps iguales |
| Reservas activas | `business_capacity_reservations_active_idx` | Filtra reserved; SUM de amount requiere medir heap reads |
| Consumo diario | indice 0036 por business/consumed_at incluye amount/order | Alineado con ventana UTC; validar selectividad |
| Notification sender | status/scheduled y type/status/scheduled | Alineado con claim por lote; medir queue lag y retry rows |
| Expiration jobs | indices parciales por status/deadline | Alineados; falta demostrar frecuencia del runner |
| Admin dashboard/metrics | indices generales + cache 5 s | Varias agregaciones; medir una ejecucion cold por cardinalidad |

## 10. Cache Permitido Y Prohibido

### Candidatos Permitidos Con Condiciones

| Dato | Key/scope propuesto | TTL inicial a medir | Invalidacion | Fallback | Datos prohibidos | Prueba obligatoria |
| --- | --- | --- | --- | --- | --- | --- |
| Marketplace publico | filtros + cursor + limit + version de schema | 15-30 s; hoy 30 s | ad/order/capacity publicable | DB | wallets, cuentas, risk/trust internos | cold/warm, aislamiento y ad tomado no reaparece |
| Perfil publico negocio | business id + version publica | 30-60 s | cambio de perfil publicable | DB | datos privados, PIN, metodos completos | DTO allowlist y invalidacion |
| Snapshot reputacion publico | business id + published_at/version | 1-5 min | nuevo snapshot durable | DB | ratings individuales/agregados vivos | anti-inferencia y minimo de ratings |
| Copy/config publica | build hash | inmutable por build | nuevo deploy | bundle | secretos/env privada | scan de bundle |
| Attention summary | user id hash interno + surface + version | 5 s max, solo si se aprueba | nuevos eventos/ack | DB | cuerpos, datos de pago, cross-user | aislamiento multiusuario y stale signatures |
| Admin dashboard | actor scope/rol + version | 5-15 s | mutaciones administrativas | DB | cache compartido entre permisos | RBAC y invalidacion |

### No Cachear Como Autoridad

- estado de orden usado para mutar;
- saldos, ledger y creditos;
- capacidad final o limite diario para reservar;
- payment instructions completas, Zelle completo o wallet privada;
- Pago Movil/receiver-details completos;
- signed URLs, evidencia o comprobantes;
- chat privado y soporte privado compartido;
- permisos/RBAC y ownership como decision final;
- resultados de locks, idempotencia o transiciones financieras.

Una cache miss o Redis caido nunca puede autorizar una accion. Las mutaciones
deben volver a PostgreSQL y fallar cerrado cuando la autoridad no esta disponible.

## 11. Observabilidad Actual Y Huecos

### Ya Existe

- `X-Request-Id`, correlation ID, operation ID y surface normalizados.
- log `backend_request_completed` con route template, status y duration.
- redaccion antes de emitir logs.
- `X-NODO-Process-Time-Ms` y `Server-Timing: app`.
- profiling interno/staging opt-in para marketplace y algunas mutaciones.
- telemetria frontend opcional con acciones, pantallas, fallos y tiempos.
- job runs, contadores de notification sender y watcher USDC.
- build/version trazable en endpoints publicos.

### Falta Antes De Produccion

- p50/p95/p99 por route template y surface con ventana temporal.
- DB acquire wait, pool saturation, conexiones activas/idle y timeouts.
- DB query time por familia, sin SQL crudo ni IDs.
- Redis error rate, latency y comandos por namespace, sin keys de usuario.
- queue depth, oldest scheduled age y retry age de notification jobs.
- last successful run y lag del expiration worker.
- watcher RPC latency/error/rate, sin tx hash o wallet como label.
- memoria/CPU/restarts por replica y build id.
- alertas y SLO Owner aprobados.

Labels permitidos: route template, metodo, status class, error code allowlist,
surface, job type, dependency y build. Prohibidos como labels: user_id,
order_id, business_id, wallet, telefono, ticket_id, tx hash o file id.

## 12. Frontend Y Assets

Build local de produccion ejecutado con Node local aprobado:

| Ruta | Size | First Load JS |
| --- | ---: | ---: |
| `/` Cliente | 1.52 kB | 104 kB |
| `/business` Negocio | 50.5 kB | 153 kB |
| Shared | - | 103 kB |

El export contiene 36 archivos, 1,629,949 bytes totales sin comprimir;
1,270,022 bytes JS y 119,408 bytes CSS. Estos totales incluyen chunks para
mas de una ruta y no sustituyen la medicion transferida/comprimida del browser.

Cloudflare headers observados en repo:

- HTML Cliente/Negocio: `no-store`.
- `/_next/static/*`: `public, max-age=31536000, immutable`.
- asset publico principal: `telegram-welcome.jpg`, 186,898 bytes.

No se observo service worker. El API base se fija en build con
`NEXT_PUBLIC_API_BASE_URL`.

## 13. Evidencia Historica De Carga

La evidencia de julio es `HISTORICAL`, no baseline del HEAD actual:

- `slice_30A_marketplace_1000_cloud_ladder_summary.json` reporto 3000/3000
  HTTP 200 a c1000 en marketplace, pero p95 cliente de 24.58 s frente a p95
  backend de 102 ms. Fue un pass funcional con UX inaceptable y no cubrio
  ordenes, chat, pagos ni admin.
- `slice_33J` fallo estricto c250 por un `READ_TIMEOUT` en 2000 requests.
- `slice_33K` elimino el timeout al limitar cada paso a c100 dentro de una
  navegacion c250, señalando forma de burst/entrega mas que una query unica.
- Esos runs crearon usuarios sinteticos que no pudieron borrarse por evidencia
  audit append-only. Repetir grandes cargas en staging tiene costo y contamina
  datos operativos aunque no borre auditoria.

Politica recomendada:

- c10/c25/c50: `product-gate` de staging.
- c100 o mas: `infra-probe` explicito, nunca unica base para readiness de producto.
- Siempre separar requested/actual, cold/warm cache, errores crudos/recoveries,
  backend process time, TTFB/connect y tiempo total cliente.

## 14. Verificacion Publica Minima De Staging

Consulta unica por endpoint, alrededor de 2026-08-05 13:00 ET. No fue carga.

| Recurso | Resultado |
| --- | --- |
| Backend `/version` | 200, build `5ef237d0b916f487405cf10f57d16605fbc93b40`, environment staging |
| Backend `/health` | 200, mismo build |
| Backend `/ready` | 200, database ok y redis ok en una muestra |
| Cliente `https://nodo-staging.pages.dev/` | 200 |
| Negocio `https://nodo-staging.pages.dev/business/` | 200 |

El SHA de staging no coincide con el HEAD local `1828a5c...`. Esto no es un
fallo de deploy en este slice: el worktree local contiene trabajo no publicado.
No se hizo smoke autenticado ni se valido el bundle contra cada flujo.

## 15. Modelo De Pruebas Baratas Y Repetibles

Docker esta disponible localmente (cliente y servidor 29.3.1). El repo ya tiene
PostgreSQL 16 y Redis 7 en `docker-compose.local.yml`.

No hace falta agregar k6 para 47P0: los harness Python actuales ya usan httpx,
concurrencia, percentiles, guardrails y JSON de evidencia. k6 sigue siendo una
opcion open-source sin licencia pagada si mas adelante se necesita arrival-rate
preciso; agregaria instalacion y mantenimiento que hoy no aportan evidencia
unica.

Playwright tampoco debe agregarse por intuicion. Se puede usar el runner local
del agente para un smoke puntual; una dependencia persistente requiere que 47P0
defina fixtures autenticados y screenshots libres de datos sensibles.

### S0 - Local Sanity

- PostgreSQL/Redis desechables y base con nombre local validado.
- 1 Cliente, 1 Negocio, 1 orden Zelle y 1 orden USDT.
- Flujo chat-first completo, Pago Movil estructurado y rating.
- USDC solo con verifier simulado/local; cero RPC o pago real.
- Evidencia: status, tiempos, request IDs e invariantes DB.

Bloqueo actual: `local_smoke.py` y `local_surface_cross_smoke.py` necesitan
reconciliarse con el flujo actual antes de considerarlos autoridad.

### S1 - Lanzamiento Pequeno Local

- 10 usuarios concurrentes, 3 negocios.
- marketplace, crear orden, chat en ordenes distintas y attention.
- Baseline c1 y c10, cold y warm.
- p95 objetivo: `OWNER_DECISION_REQUIRED` despues del baseline; no inventado.
- Invariantes: cero estados imposibles, cero duplicados y cero cross-user data.

### S2 - Concurrencia Critica PostgreSQL

- 50 clientes por el mismo anuncio: uno gana.
- 50 mensajes en ordenes distintas: sin mezcla ni duplicado.
- replay/doble click en report-payment y confirm-payment.
- pago vs cancelacion y pago vs expiracion.
- dos anuncios concurrentes contra disponibilidad declarada.
- notification jobs deduplicados y capacidad/credito exactos.

### S3 - Carga Controlada Local

- 100 usuarios, 5-10 minutos, sin archivos ni proveedores externos.
- Medir RPS, error rate, p50/p95/p99, backend time, DB acquire, CPU y memoria.
- Mezcla realista, no 100 usuarios golpeando todos la misma ruta a la vez salvo
  escenario de burst separado.

### S4 - Staging Smoke Limitado

- Solo con aprobacion, fixtures y cleanup documentado.
- c10, luego c25, luego c50 product-gate.
- Nada de archivos, notificaciones masivas, RPC USDC ni usuarios sinteticos
  ilimitados.
- c100+ solo como infra-probe autorizado y separado del gate de producto.

## 16. Plan Por Mini-Slices

### 47P0 - Baseline Y Harness Local

Objetivo: reconciliar los scripts con chat-first y producir c1/c10 repetible.

- Actualizar solo harness/fixtures, no runtime.
- Un negocio puede tener maximo un anuncio activo por metodo; para carga se
  deben crear mas negocios, no evadir el guard con muchos anuncios Zelle.
- Separar setup, warmup, medicion e invariantes.
- Guardar SHA, config no secreta, requested/actual y archivo de evidencia.
- Rollback: borrar solo scripts/evidencia nuevos; DB Docker desechable.

### 47P1 - Concurrencia PostgreSQL

Objetivo: probar locks/transacciones reales del HEAD actual.

- Races de orden, capacidad, active limit, payment/cancel/expire, confirm y ads.
- Redis local para replay/locks; repetir con Redis degradado donde sea seguro.
- No usar TestClient/in-memory como unica evidencia.
- Rollback: destruir contenedores/volumen sintetico, nunca staging.

### 47P2 - Polling Y Costo Frontend

Objetivo: medir requests por sesion y corregir solo hotspots demostrados.

- attention, chat, soporte y Admin.
- visible-only, no overlap, backoff, jitter y cancelacion de requests donde
  falten, despues de caracterizacion.
- Preservar frescura de chat y avisos; no agregar WebSocket automaticamente.
- Rollback: feature flag o revert del mini-slice frontend.

### 47P3 - Indices Con EXPLAIN

Objetivo: usar PostgreSQL real con datos sinteticos representativos.

- Marketplace lateral capacity, attention updated_at, messages, support,
  dashboard y jobs.
- Capturar plan, buffers, rows estimated/actual y tiempo cold/warm.
- Crear indice solo si mejora el query objetivo y no penaliza escrituras de
  forma desproporcionada.
- Toda migracion requiere aprobacion separada y up/down.

### 47P4 - Observabilidad Minima

Objetivo: diagnosticar saturacion sin datos sensibles ni labels cardinales.

- Pool, query families, Redis, queue lag, job freshness, RPC, CPU/memoria,
  restarts y build.
- Alertas sobre error rate, pool saturation, queue age y missing scheduler run.
- Sampling y retencion para controlar costo.
- No agregar un proveedor pago sin decision Owner.

### 47P5 - Staging Smoke Controlado

Objetivo: validar entrega real a c10/c25/c50 con usuarios sinteticos acotados.

- Verificar SHA, health/ready, frontend/API origin y flujo autenticado.
- Medir backend vs connect/TTFB/client.
- Cleanup y evidencia de filas retenidas por auditoria.
- Detenerse ante costos, rate limits, Telegram/RPC real o error creciente.

### Slice 47 Final - Production Gate

Requiere:

- SLO y presupuesto Owner;
- baseline actual y product-gate c50;
- concurrencia PostgreSQL real;
- scheduler/queue freshness demostrados;
- backup/restore con RPO/RTO;
- smoke autenticado movil;
- alertas y rollback probados;
- revision de cache headers privados.

Ningun PASS aislado de c100+ reemplaza estos requisitos.

## 17. Decisiones Owner Requeridas

1. Usuarios concurrentes y operaciones/dia esperados para lanzamiento.
2. SLO p95/p99 por marketplace, mutaciones y chat.
3. Error budget y ventana de medicion.
4. Presupuesto mensual por Railway, PostgreSQL, Redis, storage, egress y RPC.
5. RPO/RTO y retencion de evidencia/adjuntos.
6. Maximo de usuarios sinteticos permitidos en staging por auditoria append-only.
7. Si c50 es suficiente como product-gate inicial.
8. Si se autoriza instalar k6/Playwright como dependencias mantenidas o se
   conserva el harness Python y smoke puntual del agente.

## 18. Que Puede Costar Dinero

- compute y replicas Railway;
- conexiones, CPU, storage y egress PostgreSQL/Supabase;
- comandos y memoria Redis/Upstash, especialmente polling e idempotencia;
- storage/egress de adjuntos y signed URLs;
- RPC Base/USDC del watcher;
- builds/egress de Cloudflare segun plan;
- retencion de logs, metricas y evidencia de carga;
- datos sinteticos retenidos por auditoria append-only.

No se estiman dolares sin plan/proveedor y volumen Owner aprobados.

## 19. Que No Debe Optimizarse Todavia

- No migrar a microservicios.
- No agregar WebSocket por intuicion.
- No cachear ordenes, chat, datos de pago, capacidad o creditos.
- No aumentar workers/pool sin conocer `max_connections` y memoria.
- No agregar indices sin EXPLAIN.
- No reducir validaciones, locks, auditoria o idempotencia para ganar latencia.
- No convertir c100+ en objetivo de producto antes de resolver c10/c50 realista.

## 20. Validacion Ejecutada

- `git status --short --branch` y `git rev-parse HEAD`.
- `git diff --check`: exit 0, warnings CRLF preexistentes.
- busquedas `rg` de polling, routes, locks, cache, rate limits, idempotencia,
  jobs, queries, indices, observabilidad y archivos.
- Docker version: cliente/servidor 29.3.1; no se levantaron servicios.
- build web inicial sin Node en PATH: fallo ambiental esperado.
- build web repetido con runtime local aprobado: PASS.
- consultas publicas unicas a staging: version/health/ready/Cliente/Negocio 200.
- No se ejecutaron suites pytest, migraciones, EXPLAIN, carga ni smoke
  autenticado porque este slice solo mapea.

## 21. Confirmaciones

- No deploy.
- No produccion.
- No migraciones en staging o produccion.
- No carga agresiva contra staging.
- No datos borrados.
- No secretos impresos ni agregados.
- No cache ni indices implementados.
- No cambios de flujo Cliente/Negocio.
- No cambios en pagos, Zelle, USDT, USDC, creditos, capacidad o reputacion.
- No commit.
- No `READY_FOR_REAL_USE`.
