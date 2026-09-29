# Ensayo PostgreSQL 0065 aislado: bloqueo resuelto y validacion local

Fecha: 2026-09-29, America/New_York.
Estado: ENSAYO_LOCAL_PASS_12_COMPROBACIONES; PENDIENTE_REVISION_DILITAN.
Codex prepara y ejecuta; Dilitan revisa. No es una aprobacion de produccion.

## Entrega Git posterior al ensayo

Carlos aprobo con "Dale" publicar el ejecutor y el reporte en la rama de revision. Esta seccion reemplaza SOLO el pendiente de publicacion local de las secciones historicas; no cambia los resultados de las pruebas ni constituye aprobacion de Dilitan.

- [Rama de revision](https://github.com/Goldempire-coder/NODO/tree/codex/credit-holds-postgres-drill-20260929).
- Ejecutable publicado: commit 147cf3fd7c2f623523c6930c10964c5257184048, verificado con git ls-remote despues del primer push.
- Base de esta entrega: codex/integration-reviewed-fixes-20260929, SHA 2537c8e78c8fbf7ee31178a1d07deea2d5a17945. El PR debe apuntar a esa base, NO main. El reporte se incorpora en un commit documental posterior; el HEAD final y el enlace de revision se registran en PRESENCIA-CODEX.md tras comprobar la entrega.
- Archivos exclusivos: scripts/validate_credit_holds_isolated.py y governance/owner_reviews/REPORTE-2026-09-29-postgres-0065-aislado.md.
- El ejecutor conserva SHA256 0fb102ede2f7152811529823928a13ad6402fc59deba77e5516a0e1cae7f9414, igual al ensayo satisfactorio. No se modificaron apps, database, website, laboratorio de respaldos ni workflows.
- Preflight nuevo, solo lectura: Cloudflare nodo-staging muestra No Git connection; Railway nodo-api-staging / nodo-api muestra Source vacio con Connect Repo/Connect Image. Los dos workflows del checkout solo tienen workflow_dispatch; no se invocaron. No existen hooks activos locales en el directorio de hooks ni core.hooksPath configurado.
- Se comprobaron las ramas remotas antes de publicar: integrada 2537c8e, base anterior 6069a75 y main 74e6d26; la rama del ensayo aun no existia. Push normal unicamente a la rama del ensayo, sin force ni cambios a main o al PR #5.
- Ruff check y format --check se ejecutaron nuevamente: correctos. secret-guard del ejecutor: No findings. Las pruebas PostgreSQL, guardias y suite citadas debajo son evidencia del ciclo anterior, NO nuevas ejecuciones de esta publicacion.
- secret-guard del reporte actual: salida 1 por tres avisos genericos de entropia, dos por la ruta de este reporte y uno por el enlace Drive de la revision anterior. Revisados como falsos positivos; no se agregaron excepciones ni se publicaron secretos.
- La CLI gh no tiene sesion; no se extrajeron credenciales ni se inicio otra autenticacion. Se utiliza la sesion GitHub del navegador para la revision. Si la apertura no se completa, el enlace de rama anterior permite la entrega sin afirmar un PR inexistente.

Comandos de control usados desde NODO-credit-holds-review (cada invocacion Git incluye safe.directory solo para este checkout):

```text
git status --short --branch
git ls-remote --heads origin refs/heads/codex/integration-reviewed-fixes-20260929 refs/heads/codex/credit-holds-postgres-drill-20260929 refs/heads/main refs/heads/codex/review-automatic-order-transitions-20260928
git diff --cached --check
git commit -m "test: agregar ensayo PostgreSQL aislado de creditos y rollback"
git push -u origin HEAD:refs/heads/codex/credit-holds-postgres-drill-20260929
```

El comando opt-in para reproducir el ensayo y todos sus limites se conservan debajo. Publicar el script NO lo ejecuta: exige la opcion explicita, usa una carpeta nueva y PostgreSQL 17.10 local ya instalado. No se publican clusters, result.json, bitacoras ni claves ficticias. El contenido de result.json se resume mediante comprobaciones, retornos y hash.

Sigue pendiente la revision de Dilitan de esta entrega. Cualquier fusion, migracion real, staging, deploy o lanzamiento necesita el alcance y autorizacion correspondientes. No se toma otra tarea ni se cierra el ciclo por el solo hecho de publicar.

## Resumen

El bloqueo de arranque quedo resuelto bajo la indicacion posterior de Carlos "Dale resuelvelo". Se corrigio SOLO el ejecutor del laboratorio: COMSPEC explicito local, salida de procesos a archivo en vez de pipes y dos nombres de columnas de los datos ficticios. No se cambio el producto ni sus migraciones.

Resultado nuevo: PostgreSQL 17.10, 12 comprobaciones aprobadas en 11.31 segundos, salida 0 y cierre automatico confirmado. Se aplicaron 0001-0064 en una base nueva, se comprobo 0065 up/down/up, rechazo atomico de duplicados y tres carreras reales con conexiones distintas, espera de lock observada y un solo efecto en saldo/ledger. Hubo ademas 10 casos de guardia y 2 de entorno aprobados en memoria, sin procesos ni conexiones.

La base y el servicio preexistentes no se utilizaron ni modificaron; no hay listener en 56465 ni postmaster.pid del ultimo laboratorio. Las secciones anteriores al encabezado "Resolucion y evidencia nueva" conservan el historial del bloqueo, no describen el estado final. La revision nueva de Dilitan todavia NO existe para este resultado. No se autoriza migracion real ni produccion.

## Historial conservado del primer ciclo

Carlos respondio "Dale" al siguiente paso propuesto: comprobar el cambio de base de datos y su reversion en un entorno separado antes de aplicarlo a NODO. Se preparo un ejecutor exclusivo para datos ficticios, sin utilizar la configuracion de la app ni el PostgreSQL existente. El intento se detuvo al crear el laboratorio: initdb.exe se cerro con una excepcion registrada por Windows. No se creo el cluster, no se inicio un servidor nuevo y no se ejecuto SQL.

La aprobacion anterior de los cuatro paquetes por Dilitan se conserva. Este bloqueo no demuestra un fallo del codigo de creditos: ese codigo todavia no se alcanzo en el ensayo. Tampoco demuestra que la prueba pendiente este resuelta.

## Identidad y archivos

- Repositorio original preservado: C:\Users\carlo\Documents\Playground\NODO.
- Checkout reutilizado: C:\Users\carlo\Documents\Playground\NODO-credit-holds-review.
- Base y HEAD actual: 2537c8e78c8fbf7ee31178a1d07deea2d5a17945.
- Codigo integrado anterior: 50bcb67788d310ad3a5b7019338b13168ae8fbca.
- [PR #5 aprobado por Dilitan](https://github.com/Goldempire-coder/NODO/pull/5), sin merge ni deploy.
- [Rama publicada del candidato](https://github.com/Goldempire-coder/NODO/tree/codex/integration-reviewed-fixes-20260929).
- Rama nueva SOLO LOCAL: codex/credit-holds-postgres-drill-20260929. No se publica ni se crea otro PR en este ciclo, porque el ensayo queda bloqueado.
- Archivo nuevo: scripts/validate_credit_holds_isolated.py.
- Archivo nuevo: governance/owner_reviews/REPORTE-2026-09-29-postgres-0065-aislado.md (este reporte).
- Coordinacion: actualizacion de PRESENCIA-CODEX.md local/Drive, conservando el historial.

No hay cambios en los archivos rastreados del producto frente a 2537c8e. Los archivos nuevos permanecen sin commit. El ejecutor final incorpora captura numerica del codigo de salida de cada proceso; esa adicion se reviso estaticamente despues del fallo, sin otro intento de initdb.

SHA256 del ejecutor final: 7dd641af1c622e67758820bcd0a1c51a0ca2140602ad92dab8a5b409af98a738.

## Preflight comprobado

- PostgreSQL nativo instalado en C:\Program Files\PostgreSQL\17\bin, versiones de archivo 17.10.
- postgres.exe --version devolvio postgres (PostgreSQL) 17.10.
- Python existente del proyecto: 3.14.0; psycopg y Ruff ya disponibles. No se instalaron componentes.
- Disco C con 680352935936 bytes libres en la consulta inicial. Esto es evidencia de espacio, no de cifrado.
- Servicio Windows postgresql-x64-17 ya estaba Running/Automatic y permanecio asi. No se leyo su configuracion, no se conecto a el ni se cambio su estado.
- Puerto propuesto 56465 libre antes y despues del intento, verificado por Get-NetTCPConnection; el ejecutor tambien comprueba bind local antes de crear su carpeta.
- Docker no fue iniciado ni usado. No se uso Railway, Cloudflare, Supabase o R2.

## Protecciones preparadas

- Solo acepta --run-synthetic-only. No acepta URL, credenciales externas ni directorios de datos existentes.
- Crea una carpeta temporal nueva con prefijo nodo-credit-0065- en C:\Users\carlo\AppData\Local\Temp.
- Limpia el entorno heredado y solo conserva SystemRoot/WINDIR; genera TEMP/TMP y referencias libpq locales nuevas.
- Credencial aleatoria exclusivamente ficticia/local; no se imprime ni se entrega por Drive/Git. Se conserva solo junto a las evidencias ficticias locales. No sirve para NODO.
- No importa main/config ni carga archivos .env. Una guardia rechaza su apertura, conexiones Python/DNS y programas externos salvo los tres binarios PostgreSQL identificados.
- La guardia Python NO es un firewall del sistema ni intercepta las conexiones nativas de libpq. Estas estan delimitadas por parametros explicitos 127.0.0.1:56465, usuario ficticio, SCRAM y comprobacion de ruta/puerto/version antes de cualquier escritura.
- Se propone escuchar solo en 127.0.0.1, con reglas HBA SCRAM y rechazo de otras direcciones. Esa configuracion no llego a escribirse porque initdb fallo antes.
- Hay limites de conexion, consulta, espera de locks y procesos, y un plazo del ejecutor. No son un limite de costo cloud: no hay recursos cloud en esta prueba.
- Parada prevista: pg_ctl -D del directorio NUEVO -m fast -w -t 20 stop; verificar status=3 y ausencia de postmaster.pid. Nunca detener servicios por nombre o todos los procesos PostgreSQL.
- No hay registro de servicio Windows, cron, autoinicio, borrado recursivo, cambios en firewall ni reintentos dentro del ejecutor.

## Casos preparados, todos pendientes de PostgreSQL

1. Construir el esquema vacio con los 64 archivos previos exactamente como estan en el candidato, cada uno en transaccion; no usar apply_local_migrations.py, que carga configuracion local y ofrece un reset de esquema.
2. Crear registros ficticios y probar 0065 up -> down -> up, comparando indices y contenido de credits_ledger, credit_wallets y ads.
3. Para release, consume y expire, introducir duplicados ficticios antes de 0065 y exigir rechazo atomico sin indices parciales ni cambios en esos registros.
4. Con 0065 activo, exigir que un duplicado se rechace y que el cambio de saldo en la misma transaccion tambien se revierta.
5. Ejecutar dos conexiones separadas por tipo de operacion sobre el mismo objeto. Coordinar las lecturas iniciales y observar una espera REAL en pg_blocking_pids antes de dejar terminar la primera transaccion.
6. Exigir un solo efecto en saldo y ledger; consume debe devolver CREDIT_ALREADY_CONSUMED/409 a la segunda solicitud, release/expire no deben duplicar movimientos. Comprobar enlace del anuncio para consume/expire.

Se invocan los metodos reales del mixin de creditos, no una copia de su logica. Las conexiones se sincronizan en el ejecutor para construir la carrera. Ninguno de estos casos de SQL o concurrencia llego a ejecutarse.

No cubre todas las combinaciones entre tipos distintos de operacion, permisos equivalentes a Supabase/RLS, historico real, carga de produccion ni cambios ajenos a 0065. Incluso un resultado satisfactorio futuro no autorizaria aplicar la migracion a staging ni afirmar validado un respaldo. El down retira indices; no revierte operaciones ni reconstruye saldos.

## Ejecuciones y evidencia

Comando del ejecutor, desde el checkout aislado:

```powershell
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -I -B scripts/validate_credit_holds_isolated.py --run-synthetic-only
```

### Primera invocacion: error del ejecutor

- Directorio nuevo: C:\Users\carlo\AppData\Local\Temp\nodo-credit-0065-k4ag8rp9.
- Salida 1; FAIL en preflight, TypeError; cero procesos PostgreSQL lanzados, cero migraciones.
- La guardia intentaba convertir a Path el campo executable del evento subprocess.Popen. En Windows/Python 3.14 puede ser None cuando solo se proporciona la lista args. Se confirmo en el codigo local de subprocess.Popen._execute_child.
- Correccion limitada: proporcionar explicitamente executable con la ruta ya permitida, y rechazar de forma controlada cualquier campo que no sea string. No ampliar programas permitidos.
- Diez casos ficticios de la guardia aprobados: rechaza None, cmd.exe, conexion, DNS, .env y .env.staging; permite solo los tres ejecutables previstos y un archivo ficticio. Se extrajeron las funciones require/guard por AST a memoria, sin ejecutar main ni lanzar procesos.
- result.json SHA256: 5dffdc700b426cd087cc791653665690d509e4b893dbf770f255e6b42847b626.

### Segunda invocacion: fallo nativo en initdb

- Directorio nuevo: C:\Users\carlo\AppData\Local\Temp\nodo-credit-0065-bcacnwvh.
- Salida 1; FAIL / INITDB_FAILED, etapa initdb, 0.94 segundos.
- postgres --version aprobado; initdb solicitado una vez. No se reintento despues de este fallo nativo.
- stdout/stderr de initdb vacios: initdb-initdb.log tiene cero bytes.
- Windows Application, evento 1000 del 2026-09-29 07:46:11.597 -04:00: initdb.exe 17.0.10.0; modulo ucrtbase.dll 10.0.26100.9444; excepcion 0xc0000005. Eventos 1001 posteriores corresponden al mismo incidente, no a mas ensayos.
- No se leyeron dumps, memoria de procesos ni archivos adjuntos del informe Windows.
- No existe carpeta data ni postmaster.pid; el puerto 56465 no escucha. stopped=true en el JSON significa que no quedo servidor nuevo iniciado, NO que la prueba haya pasado.
- result.json SHA256: 591b82e62b53c7b786e3cd9d05e710ecbb7292a964102ce4a37d62092c20e04d.
- El ejecutor inicial no preservo el codigo numerico individual de initdb en JSON; no se inventa ese dato. La excepcion Windows si esta comprobada por el evento independiente. Se preparo process_results para no perder ese dato en una futura ejecucion.

## Revision local y limites de la evidencia

```powershell
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -I -B -m ruff check --no-cache scripts/validate_credit_holds_isolated.py
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -I -B -m ruff format --check --no-cache scripts/validate_credit_holds_isolated.py
```

Resultados finales: All checks passed; 1 file already formatted. En la primera revision se corrigio check=False explicito y se justificaron tres capturas de excepcion que preservan el fallo y la parada; no se silencian fallos. Diez casos de la guardia aprobados. La adicion final de process_results NO tiene ensayo nativo posterior.

Las 1433 pruebas del PR #5 siguen siendo evidencia anterior, no se repitieron ni se suman a estos diez casos. Las 68 omisiones previas no pasan a ser aprobaciones. No hubo migraciones, conexiones PostgreSQL, pruebas de carrera, rollback, build frontend ni prueba en Telegram en este ciclo.

Se reviso el archivo nuevo y el diff. No se incluyeron archivos temporales ni la clave ficticia en la entrega. secret-guard sobre ejecutor y reporte devolvio 1 por un aviso generico de entropia en la linea 23 del reporte: su propia ruta documental, no una credencial. El ejecutor no genero hallazgos. No se incorporaron excepciones nuevas ni se presenta la salida automatica como verde. El diff binario de los cambios rastreados del checkout original se cotejo con la evidencia anterior y sigue identico.

## Diagnostico: hechos frente a hipotesis

Hecho: initdb falla de forma nativa antes de crear la base; no es una excepcion del modulo de creditos. El modulo ucrtbase.dll identificado por Windows NO prueba por si solo que Windows o la instalacion esten danados.

Hipotesis pendiente: el entorno deliberadamente minimo del ejecutor omite COMSPEC/PATH y puede impedir que las herramientas nativas lancen sus procesos auxiliares. La guia oficial de Windows advierte sobre COMSPEC y el codigo de pg_ctl usa CMD.EXE para la redireccion. Esa documentacion no demuestra que la omision haya causado este crash concreto. Tampoco se ha descartado otra incompatibilidad local.

Proxima correccion candidata, aun NO aplicada ni ejecutada: conservar el aislamiento definiendo rutas Windows conocidas solo dentro del proceso de prueba, sin heredar todo el entorno, sin cambiar variables globales ni el servicio existente. Primero contrastar el lanzamiento nativo y capturar su codigo; despues volver al ensayo en una carpeta nueva solo si esa comprobacion queda resuelta. No bajar permisos, desactivar seguridad, reparar/reinstalar ni pasar a datos reales para evitar el bloqueo.

Si se necesitara modificar Windows, instalar componentes o recurrir a un proveedor, se requiere una decision separada de Carlos. No se solicita a Railway intervenir y no se trasladan a Dilitan las tareas de implementacion.

## Fuentes oficiales consultadas

- [PostgreSQL 17 initdb](https://www.postgresql.org/docs/17/app-initdb.html): creacion de cluster independiente, autenticacion y directorio.
- [PostgreSQL 17 pg_ctl](https://www.postgresql.org/docs/17/app-pg-ctl.html): arranque/parada de un directorio concreto.
- [PostgreSQL 17 aislamiento](https://www.postgresql.org/docs/17/transaction-iso.html): fundamento de la relectura bajo READ COMMITTED.
- [PostgreSQL en Windows](https://wiki.postgresql.org/wiki/Running_%26_Installing_PostgreSQL_On_Native_Windows): advertencia COMSPEC; guia general, no diagnostico de este equipo.
- [Codigo oficial initdb de la rama 17](https://github.com/postgres/postgres/blob/REL_17_STABLE/src/bin/initdb/initdb.c): comprobaciones y procesos auxiliares previos a la inicializacion; referencia upstream, no prueba del binario local exacto.

## Entrega y siguiente paso

Reporte Markdown y presencia para Drive; el programa experimental permanece local sin commit/push. No se modifica el reporte de integracion aprobado, ni las tareas/revisiones de Dilitan.

Pendiente: resolver el arranque aislado con evidencia y completar las comprobaciones de 0065/concurrencia. No avanzar a una migracion real, main o deploy con esta evidencia incompleta. No se cierra el ciclo automatico ni se declara NODO listo para produccion.

Sin instalaciones, cambios de proveedores, cargos cloud, datos reales, lectura de secretos existentes, conexiones a bots/wallets, USDC, backups o restore. El website y el laboratorio de respaldos previo permanecen fuera de esta entrega.

## Resolucion y evidencia nueva

Actualizacion del 2026-09-29 posterior a "Dale resuelvelo". Se mantiene la misma rama local y HEAD 2537c8e78c8fbf7ee31178a1d07deea2d5a17945, con el ejecutor y este reporte sin commit. PR #5 y la rama integrada publicada no se modificaron. El script probado tiene SHA256 0fb102ede2f7152811529823928a13ad6402fc59deba77e5516a0e1cae7f9414.

Se leyo [la revision de Dilitan del bloqueo](https://drive.google.com/file/d/1g5jMD9arBatkCoUlHE2MFufNDHrJ1KpM/view), modificada a las 12:00:40.416Z, durante este trabajo. Esa revision se refiere al reporte ANTERIOR: deja continuar la correccion local sin modificar Windows ni instalaciones y solicita registrar el retorno numerico de initdb. Se cumplio: los tres nuevos intentos completos registran initdb=0. Su veredicto BLOQUEADO no se cambia por cuenta de Codex; se entrega esta evidencia para una nueva revision.

### Causa de initdb comprobada

Se contrastaron dos invocaciones de initdb --show, con destinos nuevos inexistentes, ejecutable absoluto, usuario ficticio, limite de 20 segundos y sin inicializar datos. El [manual PostgreSQL 17](https://www.postgresql.org/docs/17/app-initdb.html) documenta que --show muestra ajustes y sale sin inicializar.

| Entorno controlado | Retorno | Salida | Directorio creado |
|---|---|---|---|
| SystemRoot/WINDIR y TEMP/TMP locales, sin COMSPEC | 3221225477 (0xc0000005) | ambos canales vacios | No |
| Mismo entorno, agregando solo COMSPEC absoluto conocido | 0 | configuracion mostrada; 123 bytes stdout, 538 stderr | No |

La unica diferencia funcional fue COMSPEC=C:\WINDOWS\System32\cmd.exe. Se conserva el entorno limpio; NO se agrego PATH, no se heredan variables NODO y no se modifican variables globales. Esto reproduce y resuelve el fallo concreto del lanzamiento; no atribuye un defecto a Windows ni prueba el punto interno exacto del acceso invalido. Los valores mostrados por --show se retuvieron en memoria y no se publicaron; solo se verifico la presencia de la etiqueta esperada.

### Ajustes del ejecutor y fallos intermedios preservados

1. Se agrego COMSPEC solo al proceso de prueba. Primer nuevo intento: carpeta nodo-credit-0065-n3aht9xu; initdb=0, base creada y lista, pero el ejecutor quedo esperando las tuberias heredadas durante pg_ctl start. No se alcanzo SQL de NODO. Se detuvo UNICAMENTE ese cluster, verificando antes ruta/puerto en su postmaster.pid; pg_ctl stop=0 y archivo PID ausente. Al cerrar el cluster se desbloqueo la captura: FAIL/TimeoutExpired/start, 98.38 segundos. No se presenta el timeout previsto de 40 segundos como una garantia cumplida en ese intento. result.json SHA256: 1b56198a3db8b2f52079c426e7e83a08c07ff416500f9713f3f77eaf3e09b9f2.
2. Se cambio la captura a un archivo local propio, stdin DEVNULL y stderr unido a stdout, conservando ejecutables permitidos, codigos de salida y parada. [pg_ctl en Windows hereda los handles estandar](https://github.com/postgres/postgres/blob/REL_17_STABLE/src/bin/pg_ctl/pg_ctl.c); el subprocess.py instalado (3.14.0, lineas 557-565 y 1641-1647) espera los lectores de pipes y vuelve a communicate sin timeout al recuperar una excepcion. Los hechos anteriores y esas fuentes sostienen el diagnostico de captura; no se inspeccionaron handles internos ni memoria. [subprocess permite redirigir a archivos](https://docs.python.org/3.14/library/subprocess.html).
3. Segundo nuevo intento: nodo-credit-0065-yk7ki2ou; arranque y cierre automaticos correctos, 0001-0064 aplicadas, pero la fixture del ejecutor usaba min_amount_usd/max_amount_usd en ads. El esquema 0004 usa amount_min_usd/amount_max_usd. FAIL/UndefinedColumn/42703 en migration_roundtrip, 10.73 segundos. result.json SHA256: 6565498666a663ba35ef389d906ef7f45d53d63835b0089ae887bdaab0214189. Se corrigieron solo esos dos identificadores de la fixture; no se modifico el esquema ni se debilitaron verificaciones.

Las bitacoras consultadas pertenecen solo a los clusters ficticios creados por este ejecutor; no se abrieron credenciales ni configuracion de servicios existentes. No hubo reintentos automaticos internos: cada fallo se detuvo, se diagnostico y se corrigio dentro del alcance local autorizado.

### Ensayo final satisfactorio

- Comando: el mismo comando opt-in documentado arriba, desde NODO-credit-holds-review.
- Ruta de evidencia: C:\Users\carlo\AppData\Local\Temp\nodo-credit-0065-2rshraxq\result.json.
- SHA256 resultado: 2274be9ab01b2fbd04d8803176d8bc430e816313e739c4dd8006140b9142b573.
- Salida del ejecutor 0; status PASS; stopped true; duracion 11.31 segundos.
- Retornos: postgres --version=0, initdb=0, pg_ctl start=0, stop=0, status=3 (no servidor activo).
- Version real verificada: PostgreSQL 17.10, server_version_num=170010, READ COMMITTED, usuario/destino propios y puerto 127.0.0.1:56465.
- 0001-0064 se aplicaron a la base ficticia; sus 64 hashes estan en result.json. La 0065 se comprobo despues, no se omite por no figurar en ese inventario historico.
- 0065 up SHA256: 5e167bc1606dfa36047045f8d49d63e8e2a3886d2a2deedfa17d1dc2fca8688d.
- 0065 down SHA256: ec2b08b2c4f75f0f57cb323a548de5fa5b7e544e01148de711ddb6a0aadb2ebe.

Las 12 comprobaciones aprobadas fueron:

1. Identidad del cluster nuevo y acceso loopback exclusivo.
2. Esquema exacto 0001-0064.
3. 0065 up -> down -> up con tres indices validos/unicos y sin cambios en ledger, wallets y ads de la fixture.
4. Duplicados release previos: rechazo atomico de 0065, sin indices parciales ni alteracion de registros.
5. Duplicado release con 0065 activo: rechazo y rollback del cambio de saldo en la misma transaccion.
6. Dos release concurrentes: lock real observado, un cambio y un no-op, sin saldo ni ledger duplicados.
7. Duplicados consume previos: rechazo atomico.
8. Duplicado consume con indice activo: rechazo y rollback de saldo.
9. Dos consume concurrentes: un cambio y CREDIT_ALREADY_CONSUMED/409, un movimiento y enlace del anuncio correcto.
10. Duplicados expire previos: rechazo atomico.
11. Duplicado expire con indice activo: rechazo y rollback de saldo.
12. Dos expire concurrentes: un cambio y un no-op, un movimiento y enlace del anuncio correcto.

Se invocaron los metodos reales del producto. Para cada carrera se exigieron PID de conexion distintos y una espera efectiva en pg_blocking_pids; no se reemplazo la logica financiera por un mock. No se prueban aqui carreras entre operaciones de TIPOS distintos. La fixture incluye saldo bloqueado adicional para que un segundo efecto no quede oculto por saldo insuficiente; no representa una contabilidad historica completa.

### Verificacion final y alcance

- Ruff check --no-cache: All checks passed. Ruff format --check --no-cache: 1 file already formatted.
- secret-guard sobre ejecutor, reporte y presencia: salida 1 por 13 avisos genericos de entropia en rutas documentales y enlaces Drive (2 en reporte, 11 en presencia), todos revisados; cero hallazgos en el ejecutor. No son credenciales, no se agregaron excepciones y no se llama verde a la salida automatica. git diff --no-index --check desde NUL para los dos archivos nuevos: sin avisos de whitespace; salida 1 propia de archivos distintos. El diff rastreado --check sale 0.
- Revision manual del ejecutor final, sus diferencias y fixtures frente al esquema y mixin: sin hallazgos bloqueantes para este ensayo local acotado. No equivale a revision independiente de Dilitan.
- Diez casos nuevos en memoria sobre las funciones require/guard extraidas por AST: rechazos de executable None, cmd.exe directo, socket.connect, DNS y .env/.env.staging; aceptacion de los tres binarios fijados y archivo ficticio. Todos aprobados.
- Dos casos nuevos en memoria sobre el prefijo de limpieza del entorno: entorno vacio y entorno ficticio con una variable no autorizada. Se exigen solo SystemRoot/WINDIR cuando existen, COMSPEC fijo y PYTHONDONTWRITEBYTECODE; la variable no autorizada se elimina. Ambos aprobados. Ninguno ejecuta main completo, subprocess ni conexion.
- Cierre independiente: Get-NetTCPConnection devuelve cero listeners en 56465, postmaster.pid del ultimo cluster no existe, servicio preexistente postgresql-x64-17 sigue Running/Automatic.
- git diff frente a 2537c8e en apps/database/.github vacio. Diff binario del checkout original identico a la captura al empezar (23552 caracteres). Website y laboratorio de respaldos preservados.
- Las 1433 aprobadas/68 omitidas de integracion siguen siendo evidencia anterior. No se repitio la suite de la app porque no cambio el producto. No se suma esa evidencia a estas 12 comprobaciones PostgreSQL ni a los 12 casos de guardia/entorno.

Pendientes al finalizar el ensayo, ANTES de la entrega Git descrita arriba: nueva revision de Dilitan de este resultado y del ejecutor; publicacion Git del ejecutor local; aprobacion expresa y procedimiento previo a cualquier migracion en staging/datos reales; los demas gates operativos del piloto siguen separados. El ciclo del ensayo no publico la rama local ni creo otro PR. El SHA del producto publicado seguia siendo 2537c8e; el hash del ejecutor identifica exactamente el codigo local probado. Las bitacoras, clusters y claves ficticias quedan solo en carpetas locales del ensayo, sin subirse a Drive/Git y sin borrado automatico.

Se actualizan solo este reporte y PRESENCIA-CODEX.md en la carpeta acordada; no las revisiones de Dilitan. No cerrar la programacion ni declarar respaldo real o produccion validados. No hubo instalaciones, cambios globales de Windows, cambios en proveedores, cargos cloud, datos reales, secretos existentes, bots, wallets, USDC, commit, push o deploy.
