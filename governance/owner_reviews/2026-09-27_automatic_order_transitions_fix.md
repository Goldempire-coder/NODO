# Correccion local de transiciones automaticas de ordenes

Fecha: 2026-09-27.
Estado actualizado 2026-09-28: IMPLEMENTADO_LOCALMENTE; VALIDACION_FOCAL_OK;
VALIDACION_GENERAL_AISLADA_OK; POSTGRES_REAL_PENDIENTE; SIN_DEPLOY.

## Alcance y base

- Aprobacion del Owner: continuar con el primer bloqueo de ordenes automaticas
  y sus pruebas. No implica autorizacion de commit, push, deploy ni activacion
  de tareas programadas.
- Checkout: `C:\Users\carlo\Documents\Playground\NODO`.
- Rama: `codex/intake-admin-review-v2`.
- HEAD inicial y final: `a9b76514d85907115c44724900ec06f2aea401ce`.
- El Owner mantiene su acceso completo de administrador y soporte. No se
  cambiaron permisos ni se creo un rol de soporte mas limitado.
- El working tree ya contenia otros cambios. Se compararon por SHA256 los
  62 archivos preexistentes inventariados: ninguno cambio durante este trabajo.

Contratos contrastados:

- `control_plane/03_DOMAIN_RULES/ORDER_LIFECYCLE_MASTER.md`, transiciones,
  plazos y requisito de cierre atomico compartido con confirmacion manual.
- `control_plane/06_API_CONTRACTS/ORDERS_API.md`, auto-complete de respaldo.
- Gobernanza vigente: `SOURCE_OF_TRUTH.md` y `ENGINEERING_GUARDRAILS.md`.

## Problema reproducido

La tarea tomaba una lista de ordenes y despues actuaba con esa copia sin
revalidar todas las condiciones junto con la escritura. Una accion de un
participante podia cambiar la orden entre ambas operaciones.

La primera prueba local fallo antes del arreglo: una copia `delivered` pudo
consumir la reserva de capacidad aunque la orden actual ya estaba `disputed`.
Resultado RED: 1 fallo, detenido en el primer fallo; 0 intentos de conexion.
Es evidencia local con datos ficticios, no evidencia de un incidente real.

## Cambio aplicado

1. El cierre automatico reutiliza el mecanismo de cierre manual. En PostgreSQL
   bloquea la fila y vuelve a comprobar estado `delivered`, plazo vigente
   vencido y ausencia de disputa `open|in_review` antes de consumir capacidad.
2. Si la orden o el plazo cambiaron, la tarea se omite sin efectos secundarios.
   La razon automatica sigue siendo `auto_completed_after_24h`; la manual
   sigue siendo `manual_confirmed`, con su validacion de propietario intacta.
3. Las dos aperturas de disputa por vencimiento tienen operaciones atomicas.
   Cada razon fija su estado de origen y su propio plazo. No se interpreta un
   vencimiento viejo como permiso para actuar sobre una etapa posterior.
4. En PostgreSQL la disputa, el estado de la orden, sus eventos y la auditoria
   usan la misma conexion y transaccion. Ante un error se propaga la excepcion
   y el contexto de conexion ejecuta rollback. Los avisos solo se solicitan
   despues de que la operacion termina correctamente.
5. Se preservan los plazos, motivos, destinatarios, deduplicacion de avisos,
   consumo unico de capacidad y pausa de publicacion del cierre manual.
   Estas transiciones no agregan movimientos de creditos ni modifican anuncios.
6. El repositorio en memoria aplica las mismas comprobaciones bajo su bloqueo
   de ordenes, siguiendo el patron de la implementacion existente. Esto no
   sustituye una prueba de transacciones y bloqueos en PostgreSQL real.

## Archivos propios del cambio

Modificados:

- `apps/api/app/modules/jobs/order_completion.py`
- `apps/api/app/modules/jobs/order_dispute_escalation.py`
- `apps/api/app/modules/orders/memory_receiver_completion.py`
- `apps/api/app/modules/orders/postgres_receiver_completion.py`
- `apps/api/app/modules/orders/memory_repository.py`
- `apps/api/app/modules/orders/postgres_repository.py`

Nuevos:

- `apps/api/app/modules/orders/overdue_dispute_rules.py`
- `apps/api/app/modules/orders/memory_job_transitions.py`
- `apps/api/app/modules/orders/postgres_job_transitions.py`
- `apps/api/tests/test_job_order_transitions.py`
- Este reporte.

Los ajustes de imports son mecanicos y se limitan a archivos de este arreglo.
No se aplico el patch externo de otra revision ni se mezclaron sus cambios.

## Validacion ejecutada

Herramientas ya instaladas: Python del `.venv`, pytest y Ruff 0.16.5.
No se instalaron ni descargaron componentes.

Las pruebas se ejecutaron con un lanzador temporal en memoria, entorno
limpiado, `APP_ENV=test`, direcciones ficticias locales, plugins externos
desactivados, cache de pytest y escritura de bytecode desactivadas. Se
bloquearon conexiones PostgreSQL, Redis y sockets. Para la suite completa
tambien se agrego un audit hook para DNS, sockets y procesos externos.
La unica excepcion de sockets fue el par interno de loopback requerido por
asyncio en Windows, identificado por su pila de llamada.

| Comprobacion | Resultado |
| --- | --- |
| Reproduccion inicial, antes del arreglo | 1 fallo esperado; 0 conexiones intentadas |
| Pruebas nuevas del arreglo | 61 passed; 0 intentos bloqueados |
| Pruebas relacionadas, incluyendo las nuevas | 287 passed, 6 skipped; 0 intentos bloqueados; 29.55 s |
| Suite `apps/api/tests`, con `-x` | 1364 passed, 68 skipped, 1 warning; 148.56 s |
| Control de aislamiento de la suite completa | 21 intentos bloqueados; codigo final 1, NO APROBADO |
| Ruff check sobre los 10 archivos Python propios | All checks passed |
| Formato Ruff de los cuatro archivos Python nuevos | Aplicado |
| `git diff --check` | Exit 0; avisos de normalizacion CRLF/LF en dos repositorios |
| Comparacion SHA256 del trabajo previo | 62 archivos comprobados; 0 alterados |

Las 61 pruebas nuevas cubren copias obsoletas, cambio de plazo, disputa abierta
despues de la lectura del lote, estados posteriores, ejecuciones simultaneas,
dry-run, propietario del cierre manual, consumo unico y ausencia de avisos
en operaciones omitidas o fallidas. Para PostgreSQL se ejercitan los metodos
reales y `PooledConnectionContext` con una conexion simulada: comprobaciones
bajo bloqueo, orden de escrituras, uso de la misma transaccion y rollback ante
errores de escritura, auditoria, capacidad o actualizacion condicional.
No se probo SQL ni concurrencia contra un servidor PostgreSQL real.

Grupo relacionado ejecutado:

- `test_job_order_transitions.py`
- `test_jobs_notifications.py`
- `test_business_capacity_matching.py`
- `test_order_receiver_details.py`
- `test_terminal_post_payment_cooldown.py`
- `test_terminal_post_payment_cooldown_postgres.py`
- `test_order_integrity_49a_static.py`
- `test_chat_disputes.py`

Las seis omisiones de ese grupo son pruebas opt-in de PostgreSQL desechable.
Se mantuvieron desactivadas. El aviso de Starlette/httpx es de dependencias
existentes: no se instalaron reemplazos ni se modificaron versiones.

## Bloqueo de la suite general

Pytest no reporto aserciones fallidas en esta ejecucion, pero algunas pruebas
intentaron acceder a servicios y absorbieron las excepciones del bloqueo.
El lanzador devolvio codigo 1 por esa condicion; los 1364 passed NO equivalen
a una suite aislada aprobada. No se permitieron las conexiones ni se
modificaron esas pruebas para obtener un resultado verde.

El diagnostico existente imprime como maximo los primeros 12 intentos:

| Prueba | Categoria y cantidad visible |
| --- | --- |
| `test_private_cache_headers.py::test_public_and_marketplace_responses_keep_their_existing_cache_policy` | PostgreSQL 2; Redis 2 |
| `test_staging_validation_tooling.py::test_marketplace_delivery_can_use_existing_fixture_run_id` | PostgreSQL 1 |
| `test_staging_validation_tooling.py::test_marketplace_delivery_expands_users_to_consume_request_target` | PostgreSQL 1 |
| `test_staging_validation_tooling.py::test_marketplace_delivery_non_multiple_request_target_uses_ceiling` | PostgreSQL 1 |
| `test_staging_validation_tooling.py::test_marketplace_delivery_warm_mode_is_explicit_and_prewarm_separate` | PostgreSQL 1 |
| `test_staging_validation_tooling.py::test_marketplace_delivery_traffic_shape_is_reportable` | PostgreSQL 1 |
| `test_staging_validation_tooling.py::test_marketplace_delivery_filtered_search_mode_uses_one_step` | PostgreSQL 1 |
| `test_staging_validation_tooling.py::test_marketplace_delivery_step_cap_jitter_and_retry_are_reportable` | PostgreSQL 1 |
| `test_staging_validation_tooling.py::test_capacity_db_seed_api_remote_fixture_mode_is_identified` | PostgreSQL 1 |

Los otros 9 intentos no quedaron identificados en la salida. No se les asigna
causa ni prueba por inferencia y no se repitio la suite para recuperarlos.
Esta ejecucion tampoco descarta fallos intermitentes documentados previamente.

## Revision y limites

Verdicto local: acceptable with concerns. La correccion focal esta preparada
y pasa su grupo relacionado; no es autorizacion de despliegue ni cierre de
todos los bloqueos de produccion.

Pendientes:

1. Diagnosticar el aislamiento de las pruebas identificadas, sin habilitar
   conexiones reales ni atribuir los nueve intentos sin evidencia.
2. Comprobar las carreras y rollback con PostgreSQL desechable, bajo un alcance
   autorizado separado. Los dobles de prueba no demuestran bloqueo real.
3. Revisar el diff final y autorizar expresamente commit/push/staging cuando
   corresponda. No incluir los cambios ajenos del working tree.
4. La activacion del scheduler, pruebas en Telegram/staging y demas hallazgos
   del piloto siguen siendo trabajo separado. No se declara NODO listo para
   operaciones reales por este arreglo.

Sin cambios en permisos admin/soporte, frontend, website, configuracion de
proveedores, secretos, wallets, USDC, migraciones ni respaldos. Sin commit,
push o deploy. No se activo ningun servicio ni scheduler.

## Diagnostico de aislamiento, solo lectura - 2026-09-28

Estado: CAUSAS_LOCALIZADAS_PARA_LOS_12_INTENTOS_VISIBLES;
9_INTENTOS_SIN_ATRIBUCION_RUNTIME; CORRECCION_PROPUESTA_NO_APLICADA.

### Alcance de esta continuacion

El Owner aprobo el primer paso: revisar las pruebas y resultados existentes.
No se ejecutaron pruebas, importaciones de la app, construcciones ni llamadas
a proveedores. Solo se actualizo este reporte. Se preservan las correcciones
de ordenes, los permisos completos del Owner y todo el trabajo previo.
HEAD sigue siendo `a9b76514d85907115c44724900ec06f2aea401ce`.

Los archivos de pruebas y las rutas de inicializacion descritas a continuacion
no tienen diferencias frente a HEAD. Las omisiones de aislamiento localizadas
ya estaban en esa base; no son cambios introducidos por el arreglo de ordenes.
Esto no descarta otras interacciones que requieran una validacion posterior.

### Hallazgo 1: disponibilidad sin simulacion en una prueba de cache

Evidencia:

- `apps/api/tests/test_private_cache_headers.py:118`: la prueba
  `test_public_and_marketplace_responses_keep_their_existing_cache_policy`
  crea la app y visita `/ready` y `/api/v1/ready`, ademas de otras rutas.
  Solo comprueba las cabeceras de cache; no simula las dependencias.
- `apps/api/app/routes/health.py:28`: ambas rutas usan `HealthService.readiness`.
- `apps/api/app/services/health_service.py:32`: consulta base de datos y Redis.
- `apps/api/app/repositories/database.py:11` y
  `apps/api/app/repositories/redis.py:10`: los chequeos intentan conectar y
  convierten las excepciones en un resultado de dependencia no disponible.

Esto explica los cuatro intentos visibles asociados a esa prueba: dos de
PostgreSQL y dos de Redis. La ruta devuelve 503 cuando falla disponibilidad,
pero la comprobacion de cache puede pasar igualmente. Por eso pytest puede
reportar passed mientras el lanzador de aislamiento reporta fallo.

Correccion minima propuesta, solo en esa prueba:

- Simular `DatabaseRepository.check_connectivity` y
  `RedisRepository.check_connectivity` con resultados ficticios de fallo.
- Conservar todas las comprobaciones de cache y todas las rutas; comprobar
  que cada dependencia se consulta dos veces y que ambas rutas ready dan 503.
- Usar el patron local ya presente en
  `apps/api/tests/test_foundation_http.py:159`; no modificar esa otra prueba.
- No borrar `/ready`, no cambiar sus respuestas reales ni simular toda la
  ruta: se debe seguir probando el middleware de cache y la ruta verdaderos.

### Hallazgo 2: preparacion de conexiones al construir herramientas de prueba

Cadena estatica comprobada:

1. `test_staging_validation_tooling.py:40` fabrica un archivo de configuracion
   ficticio con modo staging. No se leyeron archivos de secretos reales.
2. Las siete pruebas de `MarketplaceDeliveryDiagnostics` identificadas en la
   salida crean ese objeto. Su constructor crea `RealCapacityHarness`
   (`scripts/marketplace_delivery_diagnostics.py:448`).
3. `RealCapacityHarness` construye `LocalSmoke` inmediatamente
   (`scripts/capacity_real.py:203`), incluso cuando la prueba solo quiere
   comprobar opciones, contadores o formato de resultados.
4. `LocalSmoke` aplica la configuracion ficticia y llama a `create_app`
   (`scripts/local_smoke.py:37`). En modo staging se configura el estado de
   ejecucion, no el repositorio en memoria (`apps/api/app/main.py:123`).
5. Esa inicializacion llama a `warm_pool` (`apps/api/app/main.py:360`), que
   intenta adquirir conexiones PostgreSQL. Al bloquearse la primera conexion,
   la excepcion sale de `warm_pool` y `main.py:365` la captura y registra.

Esta cadena explica los siete intentos visibles de Marketplace y el intento
de `test_capacity_db_seed_api_remote_fixture_mode_is_identified` (linea 1577).
En esta ultima prueba las simulaciones de preparacion y comprobacion de datos
se colocan despues del constructor: llegan tarde para impedir el calentamiento
de conexiones. El contenido ficticio no impide por si solo que el codigo
intente abrir una conexion; fue el bloqueo del lanzador lo que lo detuvo.

No se necesita modificar los chequeos reales de NODO para corregir estas
pruebas. Propuesta acotada a `test_staging_validation_tooling.py`:

- Preparar una fixture de aislamiento local antes de construir las herramientas.
  Simular especificamente `app.main.warm_pool`, en el punto donde se usa,
  con un sustituto sin conexion y con registro de llamadas para comprobarlo.
- Mantener los constructores, validadores y comprobaciones existentes:
  staging, allowlists, confirmaciones de mutacion, modo de fixtures, calculos,
  limites y privacidad. No sustituir todo `create_app` ni todo el harness.
- Mantener el bloqueo de conexiones PostgreSQL, Redis, DNS, sockets y procesos
  externos del lanzador. Cualquier llamada no simulada debe seguir fallando.
- Restaurar la configuracion de proceso al terminar cada prueba, con alcance
  local a ese modulo. `scripts/local_hardening_common.py:50` modifica el
  entorno del proceso y no lo restaura; el archivo de pruebas tampoco lo
  restaura actualmente. Es un riesgo estatico de contaminacion entre pruebas,
  no la atribucion demostrada de los nueve intentos restantes.
- No forzar el modo test en los fixtures que deben validar guardrails staging,
  ni modificar `main.py`, `LocalSmoke` o los scripts operativos.

### Limite de evidencia: nueve intentos no impresos

Se reviso el codigo conservado del lanzador temporal: acumula los intentos en
memoria, imprime el total y solo recorre `blocked[:12]` para mostrar detalles.
La salida existente contiene 21 como total y doce registros individuales.
No se encontro otro resultado detallado de esa ejecucion en los reportes y
archivos de evidencia consultados. No se repitio la suite para obtenerlos.

En `test_staging_validation_tooling.py` hay otros nueve constructores que
alcanzan la misma cadena. Son candidatos por lectura del codigo, NO una
recuperacion de los registros faltantes:

| Prueba candidata | Linea de definicion |
| --- | --- |
| `test_capacity_latency_isolation_aggregates_headers_and_delta` | 1638 |
| `test_capacity_records_request_error_samples_outside_latency_limit` | 1730 |
| `test_capacity_remote_client_uses_explicit_max_connections` | 1816 |
| `test_capacity_output_separates_setup_and_measured_load` | 1840 |
| `test_capacity_db_direct_ad_setup_dispatches_without_api_call` | 1890 |
| `test_capacity_output_reports_db_direct_fixture_setup_mode` | 1932 |
| `test_capacity_profile_marketplace_adds_profile_header` | 1977 |
| `test_capacity_without_profile_marketplace_does_not_add_profile_header` | 2005 |
| `test_capacity_profile_summary_aggregates_stages_without_secrets` | 2032 |

Que la cantidad encaje no demuestra su atribucion individual en la ejecucion
pasada. Falta la relacion runtime de esos nueve intentos con prueba y categoria.

Para una futura ejecucion autorizada, proponer al lanzador un resumen acotado
por archivo, nombre de funcion sin parametros, categoria y cantidad, junto con
el total y el numero de grupos omitidos si se alcanza el limite de salida.
No registrar argumentos, destinos, configuraciones ni contenido privado.
Mantener codigo de salida no cero ante cualquier intento bloqueado. No se
modifico ni ejecuto el lanzador durante este diagnostico.

### Siguiente aprobacion propuesta

Modificar unicamente los dos archivos de pruebas anteriores y este reporte.
Aplicar las simulaciones y restauracion de configuracion descritas, conservando
todas las verificaciones. Mejorar solo en memoria el resumen del lanzador,
manteniendo todas sus prohibiciones. Validar formato, pruebas focales y
relacionadas y, si pasan sin intentos bloqueados, la suite completa. Detenerse
ante un fallo distinto o una conexion bloqueada; no corregir fuera de alcance.

Criterios de aceptacion posteriores, aun NO verificados:

- Todas las comprobaciones existentes conservadas.
- Consultas de ready simuladas y contadas; rutas y politica de cache intactas.
- Construccion de herramientas sin conexiones y sin contaminacion del entorno.
- Cero intentos bloqueados en la validacion que se declare aprobada, con un
  diagnostico que no oculte intentos adicionales.
- Sin cambios de app, permisos, website, staging, proveedores, secretos,
  wallets, USDC, instalaciones, commit, push o deploy.

La concurrencia y rollback con PostgreSQL desechable siguen pendientes de
una autorizacion y prueba separadas. Este diagnostico no valida produccion.

Verificacion de alcance: de los 73 archivos modificados/no versionados
inventariados al iniciar esta continuacion, solo cambio este reporte. Los
otros 72 conservaron su SHA256. El contenido anterior del reporte se conservo
como prefijo, sin reescribir sus resultados historicos.

## Continuacion autorizada: comprobacion previa - 2026-09-28

Estado: DETENIDO_EN_LINT_PREEXISTENTE; AISLAMIENTO_AUN_NO_MODIFICADO;
SIN_NUEVA_EJECUCION_DE_PRUEBAS.

El Owner indico "dale sigue" respecto de la correccion de aislamiento
propuesta arriba. Antes de editar se inventariaron 75 archivos: el trabajo
previo y los dos archivos de pruebas objetivo. HEAD sigue en
`a9b76514d85907115c44724900ec06f2aea401ce`.

La comprobacion estatica inicial, sin autofix ni cache, fue:

```powershell
.\.venv\Scripts\python.exe -B -m ruff check --no-cache --output-format json apps/api/tests/test_private_cache_headers.py apps/api/tests/test_staging_validation_tooling.py
```

Resultado: codigo 1, 38 avisos. `git diff --exit-code HEAD --` sobre los
dos archivos devolvio 0 y ninguna diferencia: los avisos estaban presentes
antes de este ajuste. No proceden de un cambio aplicado en esta continuacion.

| Archivo | Regla | Lineas originales | Cantidad |
| --- | --- | --- | --- |
| `test_private_cache_headers.py` | I001, orden de imports | 30 | 1 |
| `test_private_cache_headers.py` | RUF100, supresiones no usadas | 30, 31 | 2 |
| `test_staging_validation_tooling.py` | I001, orden de imports | 19 | 1 |
| `test_staging_validation_tooling.py` | RUF100, supresiones no usadas | 19-37, 1835 | 20 |
| `test_staging_validation_tooling.py` | BLE001, captura generica | 1230 | 1 |
| `test_staging_validation_tooling.py` | UP037, anotaciones entre comillas | 2350, 2356, 2401, 2407, 2496 | 5 |
| `test_staging_validation_tooling.py` | RUF012, atributos mutables de clase | 2350, 2401 | 2 |
| `test_staging_validation_tooling.py` | PYI034, tipo de retorno de contexto | 2356, 2407, 2496 | 3 |
| `test_staging_validation_tooling.py` | PYI036, firma de salida de contexto | 2359, 2410, 2499 | 3 |

No son 38 pruebas fallidas ni evidencia de 38 defectos de la app. Tampoco se
declaran inocuos sin revision: los cambios de inicializacion, estado compartido
y excepciones deben conservar el significado de las pruebas.

Se respeto el criterio aprobado de detenerse ante un fallo distinto. No se
aplicaron las simulaciones de disponibilidad o calentamiento, la restauracion
del entorno ni el cambio del lanzador temporal. No se ejecuto pytest, ninguna
conexion ni servicio. No se instalaron herramientas ni se cambio la
configuracion de Ruff para ocultar avisos. Solo se actualiza este reporte.

### Siguiente bloque propuesto

Autorizar en conjunto la correccion de los 38 avisos inventariados y su
formato derivado, dentro de estos mismos dos archivos, preservando imports
con efectos de inicializacion, verificaciones, excepciones esperadas y estado
de los dobles de prueba. Despues aplicar el aislamiento ya documentado y el
diagnostico agregado del lanzador en memoria. Comprobar diff, formato,
pruebas focales y relacionadas y, si pasan sin intentos bloqueados, suite
completa. Ante otro fallo distinto, detenerse sin ampliar el arreglo.

Esto no requiere cambios en la app ni en los permisos completos del Owner.
Se mantienen pendientes la validacion aislada y la prueba separada de
concurrencia/rollback en PostgreSQL. No se declara produccion validada.

Sin commit, push, deploy, instalaciones, cambios cloud, migraciones,
secretos, wallets o USDC. Verificacion final de alcance: de los 75 archivos
inventariados, solo cambio este reporte; los otros 74 conservaron su SHA256.

## Correccion de aislamiento y validacion completa - 2026-09-28

Estado: AISLAMIENTO_CORREGIDO; LINT_OBJETIVO_OK; SUITE_AISLADA_OK;
POSTGRES_REAL_PENDIENTE; SIN_COMMIT_PUSH_DEPLOY.

### Autorizacion y archivos

El Owner indico "Ok trabaja en eso" despues del resumen del bloque pendiente.
Se corrigieron los 38 avisos y el aislamiento dentro de los dos archivos
identificados, conservando el resto del trabajo local. Archivos modificados:

- `apps/api/tests/test_private_cache_headers.py`.
- `apps/api/tests/test_staging_validation_tooling.py`.
- Este reporte, incluido su estado actual del encabezado. Las secciones
  anteriores conservan la evidencia historica, no describen el estado final.

HEAD permanece en `a9b76514d85907115c44724900ec06f2aea401ce`, rama
`codex/intake-admin-review-v2`. No se modifico la app ni se redujeron los
permisos de administrador/soporte del Owner. Tampoco se activaron jobs.

### Cambios y preservacion de controles

1. La prueba de cache sigue recorriendo todas sus rutas originales. Simula
   exclusivamente los chequeos de DatabaseRepository y RedisRepository con
   resultados ficticios no disponibles. Comprueba 503 y UPSTREAM_UNAVAILABLE
   en ambos alias de ready y exactamente dos consultas a cada dependencia.
   No se simulo la ruta, create_app ni el middleware de cache.
2. Una fixture limitada al modulo de herramientas restaura el entorno al
   terminar cada prueba. Simula `app.main.warm_pool` antes de construir los
   harnesses, registrando solamente tamanos, no direcciones ni argumentos
   privados. Los constructores y guardrails staging siguen ejecutandose.
3. Dos casos ficticios nuevos comprueban restauracion normal y ante excepcion:
   variables agregadas, cambiadas y eliminadas, y restitucion del sustituto
   de warm_pool. Una prueba existente comprueba que el constructor conserva
   staging y solicita el calentamiento simulado de tamano 3.
4. Se ordenaron imports sin moverlos antes de la preparacion necesaria del
   entorno o sys.path. Se retiraron supresiones no utilizadas. Las listas
   de los FakeClient siguen siendo de clase y creadas dentro de cada prueba;
   se anotan como ClassVar, con Self y firmas de contexto compatibles.
5. La captura generica de la prueba de rutas de migracion ahora nombra las
   dos excepciones ya esperadas. Conserva la comprobacion exacta del nombre
   de excepcion y el fallo cuando una ruta insegura no es rechazada.

Comparacion estructural AST con HEAD, que era la base sin cambios de ambos
archivos: se conservaron las 115 funciones originales de prueba y sus 380
aserciones (3 funciones / 12 aserciones en cache; 112 / 368 en herramientas).
Se agrego una funcion parametrizada en dos casos. Esta comprobacion estatica
complementa, no reemplaza, las ejecuciones ni la revision del diff.

### Ejecutor temporal y privacidad

Solo en memoria se cambio la presentacion de intentos bloqueados: agregacion
por archivo, funcion sin parametros, categoria y cantidad. Imprime el total,
hasta 100 grupos y el numero explicito de grupos omitidos. No imprime
destinos, argumentos, valores del entorno ni contenido privado. Ademas de
`-x`, pide detener la suite al terminar una prueba con un intento bloqueado,
aunque esa prueba capture la excepcion. Cualquier intento mantiene salida
final no cero. No se escribio un nuevo ejecutor en el repositorio.

Se conservaron los bloqueos de PostgreSQL, Redis, DNS, sockets y procesos
externos. La unica excepcion de sockets sigue siendo el par interno de
loopback de asyncio en Windows, identificado por su pila. Se limpio el
entorno heredado, se usaron configuraciones ficticias y se desactivaron
plugins externos, cache pytest, bytecode y los sender/watcher. No hubo
conexiones a staging ni proveedores.

### Resultados nuevos

Herramientas locales existentes, sin instalaciones. Cada ejecucion de pytest
uso un proceso nuevo, el mismo bloqueo y `-q --tb=short -x -p no:cacheprovider`.

| Comprobacion | Resultado |
| --- | --- |
| Ruff check, ambos archivos completos | All checks passed, exit 0; 38 avisos resueltos |
| Ruff format de los rangos cambiados | 21 rangos aplicados y comprobados con --check; exit 0 |
| Preservacion AST de aserciones originales | 380 conservadas, ninguna perdida; exit 0 |
| Dos archivos afectados | 117 passed, 1 warning; 4.58 s; exit 0 |
| Grupo relacionado, 12 archivos | 416 passed, 6 skipped, 1 warning; 33.53 s; exit 0 |
| Suite completa apps/api/tests | 1366 passed, 68 skipped, 1 warning; 149.32 s; exit 0 |
| Intentos bloqueados en las tres ejecuciones | 0; grupos mostrados 0; grupos omitidos 0 |
| git diff --check en los archivos de pruebas | exit 0; aviso existente CRLF/LF en herramientas |

El grupo relacionado incluyo primero herramientas staging y despues cache
privada, foundation HTTP, cache admin y los ocho archivos de ordenes ya
enumerados arriba. Esto ejercito la restauracion antes de otras pruebas en
el mismo proceso. Las seis omisiones del grupo de ordenes siguen siendo
pruebas opt-in de PostgreSQL desechable. Las 68 omisiones de la suite completa
no se cuentan como aprobadas ni se habilitaron integraciones reales.

El unico warning de las ejecuciones fue el aviso existente de Starlette
sobre TestClient/httpx. No se cambiaron dependencias. Se limito el formateo a
los rangos modificados para no reescribir el archivo completo; no se declara
que todo su formato historico haya sido normalizado.

### Revision final, limites y siguiente paso

Revision del diff acotado: sin hallazgos bloqueantes en este cambio de pruebas.
La ejecucion nueva cierra el bloqueo de aislamiento observado: cero intentos
registrados. No recupera la atribucion de los nueve intentos historicos que
el lanzador anterior no imprimio, ni descarta fallos intermitentes ajenos.

De los 75 archivos inventariados al iniciar, solo cambiaron los dos archivos
de pruebas autorizados y este reporte; los otros 72 conservaron su SHA256.
Se preservaron los arreglos de ordenes y todos los cambios ajenos, incluido
el website. No hay commit, push, deploy, migraciones, cambios de secretos,
wallets, USDC, proveedores ni activacion de servicios externos.

Sigue pendiente probar concurrencia y rollback del arreglo de ordenes contra
un PostgreSQL desechable y aislado, bajo alcance separado. Las conexiones
simuladas no demuestran comportamiento SQL real. Despues corresponde revisar
el diff de entrega y obtener autorizacion explicita para commit/push/staging.
Este cierre local no declara NODO listo para produccion ni cierra los otros
hallazgos del reporte general.

## Entrega para revision en GitHub - 2026-09-28

El Owner autorizo subir primero este bloque a GitHub y entregar el enlace
para un validador externo. Esta autorizacion no incluye deploy, migraciones,
activacion de jobs ni cambios en proveedores.

Base de la entrega: `a9b76514d85907115c44724900ec06f2aea401ce`, confirmada
tambien en la rama remota `codex/intake-admin-review-v2`. Rama de revision
prevista: `codex/review-automatic-order-transitions-20260928`. No se actualiza
la rama de origen ni `main`, no se abre un PR ni se fusiona el cambio.

El commit incluye exclusivamente los diez archivos Python del arreglo de
ordenes enumerados arriba, `test_private_cache_headers.py`,
`test_staging_validation_tooling.py` y este reporte: 13 archivos. Se excluyen
los cambios preexistentes de observabilidad, website, otras pruebas, otros
reportes y el laboratorio de respaldos. Los permisos completos del Owner
se mantienen intactos.

### Limite de la evidencia para el validador

Los resultados de 117, 416 y 1366 pruebas aprobadas corresponden al working
tree local con otros arreglos preexistentes, NO a un checkout limpio de este
commit aislado. Esos otros arreglos se preservan, pero no se incluyen en la
entrega. No se afirma que la suite completa del commit publicado haya pasado.
El validador debe revisar el diff contra la base indicada y distinguir esta
evidencia local de una ejecucion reproducida desde GitHub.

La comprobacion actual de Ruff sobre los 12 archivos Python de la entrega
paso sin avisos. Se revisaron los diffs y archivos nuevos antes de preparar
el commit. El indice contiene exactamente los 13 archivos autorizados y
`git diff --cached --check` paso. El detector de secretos sobre las lineas
agregadas produjo un unico aviso de entropia en la referencia al contrato
ORDER_LIFECYCLE_MASTER.md (linea 22): revision manual confirma que es una ruta
de documentacion, no una credencial. No se desactivo el detector ni se agrego
una lista de excepciones. No hubo otros avisos; esto no es una auditoria de
secretos de todo el historial del repositorio.

Los dos workflows del repositorio solo admiten ejecucion manual;
no se invocan. El mensaje del commit llevara el prefijo `[skip ci]`, que
[Cloudflare Pages documenta para omitir despliegues por commit](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/#skipping-a-build-via-a-commit-message).
Esto no se presenta como una garantia de configuracion de Railway: se usa
una rama nueva de revision y no se solicita ningun despliegue.

Siguen pendientes PostgreSQL real aislado, revision independiente y los
demas bloqueos del piloto. Publicar el codigo para revision no equivale a
aprobarlo para staging o produccion. El SHA final y la confirmacion remota
se entregaran al Owner despues de completar y verificar la subida.
