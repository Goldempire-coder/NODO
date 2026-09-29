# NODO: Registros Y Pruebas Pendientes Para Revision En GitHub

Fecha: 2026-09-28.
Estado: LOCAL_CANDIDATE_VALIDATED_FOR_REVIEW / NOT_DEPLOYED.

## Alcance

Continuacion de la entrega para el validador, despues de la indicacion del
Owner de dejar Drive pendiente y trabajar en lo que faltaba subir a GitHub.
No se consultaron ni modificaron carpetas, archivos o permisos de Drive.

Base publicada: `aa6b684dcf59b95d5d221db9a5842304a9b58009`.
Rama de revision: `codex/review-automatic-order-transitions-20260928`.
Se conserva el commit anterior de transiciones automaticas, sin reescribirlo.
No se modifica `codex/intake-admin-review-v2` ni la rama principal.

Este bloque incorpora cambios locales previamente preparados. La unica
edicion nueva de codigo durante esta entrega corrige tres avisos I001 de
formato/imports en logging.py y test_logging_output.py. No se cambiaron
reglas de negocio, permisos, transiciones, montos, contratos API o esquemas.

## Cambios Incluidos

1. Registros operativos JSON: campos acotados, filtros sin duplicacion y
   exclusion de cuerpos, argumentos, trazas completas y extras privados.
   Redaccion de los patrones reconocidos; no es una garantia universal de
   deteccion de cualquier dato que alguien introduzca en un campo permitido.
2. Plantillas de rutas: preservar prefijos de routers incluidos sin registrar
   los identificadores concretos ni los parametros privados de la consulta.
3. Pruebas de aislamiento: simular Telegram y chequeos DB/Redis; restaurar el
   limite temporal del watcher de creditos sin contaminar pruebas posteriores.
4. Pruebas de PIN, calificaciones y chat: alinear expectativas con el codigo y
   lenguaje vigentes, conservando los controles de permisos y persistencia.
5. Privacidad del receptor: comprobar primero los datos ficticios guardados;
   distinguir metadatos contrastados con sus registros de una exposicion real.
   Recorrer toda la respuesta, sin excluir campos solo por su nombre.
6. Documentacion de calificaciones: una frase, de operacion a orden.

Archivos seleccionados, ademas de este reporte:

- `apps/api/app/core/logging.py`
- `apps/api/app/shared/observability.py`
- `apps/api/tests/test_admin_console.py`
- `apps/api/tests/test_admin_operational_notifications.py`
- `apps/api/tests/test_admin_private_cache_headers.py`
- `apps/api/tests/test_backend_observability_foundation.py`
- `apps/api/tests/test_business_chat_order_isolation_static.py`
- `apps/api/tests/test_business_intake_bot.py`
- `apps/api/tests/test_chat_disputes.py`
- `apps/api/tests/test_foundation_http.py`
- `apps/api/tests/test_logging_output.py`
- `apps/api/tests/test_order_ratings.py`
- `apps/api/tests/test_order_receiver_details.py`
- `control_plane/08_SCREENS/remitter/R-11_RATING.md`

## Validacion Del Candidato Seleccionado

Se exporto exclusivamente el arbol Git preparado, sin cambiar el checkout
original, sin copiar .env reales, secretos, .venv ni archivos locales ignorados.
Arbol probado: `d8e8dd8836c3049a538d290d3e452a260c269056`.
La copia temporal tiene 2416 archivos. Este reporte se agrega despues y no
forma parte del codigo ejecutable probado. No se instalo ninguna dependencia.

La copia usa el website y operations/README.md ya versionados, no sus cambios
locales pendientes. Por tanto, la evidencia nueva no depende de esos cambios.

Entorno instalado reutilizado: Windows, Python 3.14.0, pytest 9.1.1,
FastAPI 0.141.1, Starlette 1.6.0, httpx 0.28.1, Ruff 0.16.5,
psycopg 3.3.4 y redis 8.1.0. No equivale a probar la imagen Python 3.12 de
Dockerfile ni todas las versiones admitidas por requirements.txt.

Se reutilizo el ejecutor temporal en memoria: entorno ficticio limpio,
plugins automaticos/cache/bytecode desactivados, emisor y watcher apagados,
DB/Redis ficticios, y bloqueo de PostgreSQL, Redis, DNS, sockets y subprocesos.
Solo se permite el socketpair interno de asyncio de Windows, identificado
por su pila. Un intento bloqueado fuerza fallo aunque una prueba lo capture.
No se agrego ni modifico conftest, pytest.ini o el ejecutor en disco.

Seleccion pytest: `-p no:cacheprovider <seleccion> -q --tb=short -x`.

| Comprobacion | Resultado | Tiempo | Intentos bloqueados |
| --- | --- | --- | --- |
| Ruff de los 13 archivos Python, incluyendo E402 | PASS | No registrado | No aplica |
| git diff --cached --check | PASS | No registrado | No aplica |
| test_logging_output.py + test_backend_observability_foundation.py | 54 passed, 1 warning, exit 0 | 3.75 s | 0 |
| Suite apps/api/tests en la copia seleccionada | 1360 passed, 68 skipped, 1 warning, exit 0 | 146.03 s | 0 |

La advertencia es la deprecacion conocida de httpx en Starlette TestClient.
Las 68 omisiones no son pruebas aprobadas. Los conteos focal y completo se
superponen; no se suman. No se ejecutaron conexiones o integraciones reales.

### Diferencia Respecto A Las 1366 Pruebas Anteriores

La evidencia anterior se obtuvo en el directorio de trabajo completo. Alli
hay dos archivos adicionales excluidos por .git/info/exclude, lineas 8-9:

- `apps/api/tests/test_staging_enrollment_reset_map_static.py`: dos pruebas.
- `apps/api/tests/test_staging_enrollment_reset_static.py`: cuatro pruebas.

Son seis pruebas locales ajenas a este bloque, ausentes del arbol publicado.
El directorio original tiene 100 archivos test*.py y la copia tiene 98.
Se conservaron ambos archivos y las exclusiones; no se uso git add -f.
No se eliminaron seis pruebas del repositorio. El resultado aplicable al
candidato de esta entrega es 1360, no 1366.

## Revision Y Secretos

Revision manual del diff completo de los 14 archivos seleccionados. No se
incluyen website, laboratorio, .env, credenciales, binarios de pruebas,
migraciones ni cambios de proveedor. Se mantienen las verificaciones de PIN,
permisos, auditoria, cache privada, persistencia y datos del receptor.

El escaner de secretos sobre las lineas preparadas senalo tres coincidencias:

- test_chat_disputes.py:1755, entropia de una ruta documental publica.
- test_logging_output.py:139, token deliberadamente ficticio usado para
  comprobar la redaccion; no procede de cuentas o servicios reales.
- Este reporte:54, entropia de la ruta documental de R-11_RATING.md.

Las tres se revisaron manualmente. No se desactivo el escaner ni se agregaron
excepciones generales. Resultado automatico con avisos, no un PASS silencioso.

Veredicto acotado: aceptable para revision externa, con limites pendientes.
Esta comprobacion no es una auditoria global de seguridad ni un go-live.

## Limites Y Pendientes

- El cambio no instala vigilancia externa ni cierra el circuito completo de
  alertas criticas. La entrega real a Telegram no se probo aqui.
- No se probaron transacciones o concurrencia contra PostgreSQL real. Las
  limitaciones del reporte de transiciones automaticas se mantienen.
- La suite paso una vez. La asercion historica de alertas que busca 202 en
  metadatos puede coincidir con un UUID; este bloque no la modifica ni declara
  resuelta su intermitencia. El validador debe revisar ese pendiente por separado.
- No se comprobaron la imagen de despliegue, la interfaz en Telegram ni el
  estado actual de staging. No hubo deploy, reinicio o consulta a proveedores.
- Recuperacion real, piloto, revision legal y produccion no quedan aprobados
  por subir este bloque ni por obtener una suite local sin fallos.

## Entrega Y Trabajo Preservado

Se prepara un commit adicional de revision, con prefijo [skip ci], sin PR,
merge, force-push ni cambio de ramas de despliegue. Los dos workflows del
repositorio consultados se disparan solo manualmente; no se invocan.
El prefijo no se presenta como garantia general de comportamiento de Railway.

Quedan fuera los cambios del website, operations/README.md, los programas
operations/backup_cloud y los reportes historicos no versionados de piloto,
alertas y respaldos. Requieren su propia seleccion y revision antes de subir.
Este reporte resume el bloque entregado; no sustituye ni borra su historial.

Inventario inicial: 62 archivos modificados/no versionados. Los hashes
confirmaron cambios solo en los dos archivos de formato indicados; ademas se
agrego este reporte. Los otros 60 archivos conservaron exactamente sus bytes.
El SHA de entrega y la verificacion remota se informan al finalizar la subida.
No se tocaron Drive, datos reales, secretos existentes, wallets ni USDC.
