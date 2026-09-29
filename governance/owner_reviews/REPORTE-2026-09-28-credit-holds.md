# NODO - TAREA-000: movimientos de creditos repetidos

Fecha local: 2026-09-28 (America/New_York).
Autor: Codex. Revisor previsto: Dilitan.
Estado: correccion y validacion local completas; publicacion de la rama bloqueada por verificacion pendiente de Cloudflare. No es cierre de tarea ni aprobacion para produccion.

## Resumen

Codex comprobo y corrigio el intervalo entre consultar un movimiento y obtener el bloqueo del saldo. Si otro proceso habia terminado mientras el segundo esperaba, se podia repetir el movimiento. La prueba ficticia fallo antes del cambio y paso despues.

Se conservaron los contratos: release y expire duplicados no vuelven a mover creditos; consume duplicado mantiene CREDIT_ALREADY_CONSUMED, HTTP 409. No se convirtio ese error contratado en un exito silencioso.

Dilitan revisa el resultado; Codex implementa y resuelve sus observaciones. No se pide al revisor que programe ni que investigue en lugar del constructor.

## Base y aislamiento

- Repositorio original: C:\Users\carlo\Documents\Playground\NODO.
- Base: 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1, rama codex/review-automatic-order-transitions-20260928.
- [Base publicada](https://github.com/Goldempire-coder/NODO/tree/6069a75ee2fa6f9b05fdf21ebbfc77039af562c1).
- Worktree aislado: C:\Users\carlo\Documents\Playground\NODO-credit-holds-review.
- Rama local: codex/credit-hold-idempotency-20260928.
- Commit local del codigo probado: fc53e5e20d8d22c2cad1a3e5ff7972b23748951f.
- No se hizo push. La rama y ese commit todavia no son una entrega accesible en GitHub; no se proporciona un enlace remoto como si estuviera publicado.
- No se creo PR. No se fusiono ni se modifico main.
- Se inspeccionaron los worktrees existentes. El ayudante de la app no pudo resolver la referencia del repositorio anidado; se uso git worktree add en NODO con destino inexistente comprobado, no un clon.
- Comparacion del status y diff original antes/despues de la correccion: identicos. Website, operaciones y laboratorio preservados. Las actualizaciones documentales propias de esta entrega se distinguen de esos cambios.

## Comprobacion contra codigo y contratos

El contrato CREDITS_AND_BILLING_MASTER mantiene las reglas de bloqueo, consumo, liberacion y vencimiento. BUSINESS_ORDERS_API conserva el 409 para doble consumo no amparado por repeticion idempotente.

Los procesadores de expiracion llaman expire_hold; no deben describirse como llamadores directos de release/consume. Se comprobo el mismo intervalo vulnerable en expire_hold_in_transaction, dentro del mismo modulo, y se incluyo una revalidacion identica. Es una correccion relacionada de dos lineas, no una sustitucion de los workers ni una nueva regla de negocio.

Las rutas de disputas y ordenes tienen otros bloqueos. Este hallazgo del modulo compartido no demuestra que todos sus llamadores permitan simultaneidad ni que haya ocurrido una duplicacion real. No se inspeccionaron datos de clientes ni saldos reales.

## Archivos del commit de codigo

1. apps/api/app/modules/ads/postgres_credit_holds.py: siete lineas nuevas; segunda comprobacion despues del bloqueo del saldo para release, consume y expire.
2. apps/api/tests/test_credit_hold_idempotency.py: 18 casos ficticios de intercalado, repeticion, saldo insuficiente, movimientos independientes y rollback ante fallo de insercion.
3. apps/api/tests/test_credit_hold_migration_static.py: cuatro comprobaciones estaticas del SQL y su reversa.
4. database/migrations/0065_credit_hold_idempotency.up.sql: tres indices unicos parciales preparados, no aplicados.
5. database/migrations/0065_credit_hold_idempotency.down.sql: reversa preparada, no ejecutada.

Diff del codigo: cinco archivos, 297 inserciones; solo siete lineas nuevas en codigo de la app. No se modificaron pruebas anteriores.

## Defensa y limites

Las guardas iniciales siguen presentes. Tras FOR UPDATE se consulta nuevamente el movimiento, antes de modificar el saldo. Esto cubre el intercalado bajo READ COMMITTED: la sentencia posterior puede observar la transaccion que termino mientras esperaba el bloqueo.

Referencia oficial: [PostgreSQL 17, Transaction Isolation](https://www.postgresql.org/docs/17/transaction-iso.html). No se encontro un cambio de aislamiento en el codigo buscado, pero no se consulto la configuracion efectiva de una base real.

Los indices preparados cubren release por related_ad_id, consume por related_order_id y expire por related_ad_id. Son por tipo y clave no nula, no una garantia universal entre tipos distintos. Referencia: [PostgreSQL 17, Unique Indexes](https://www.postgresql.org/docs/17/indexes-unique.html).

No se agrego ON CONFLICT DO NOTHING: ignorar una insercion despues de modificar el saldo podria confirmar un efecto sin su movimiento. Un error sigue propagandose y el contexto transaccional existente hace rollback. La prueba inyecta un error ficticio de insercion y verifica ausencia de commit y restauracion del saldo; no prueba una violacion de indice ejecutada en PostgreSQL.

Quedan fuera de la demostracion: carreras entre tipos diferentes, todos los posibles intercalados de todo el sistema y el estado historico de los datos. No se declara eliminada cualquier forma de concurrencia.

## Pruebas nuevas de esta ejecucion

Entorno instalado: Windows y Python 3.14 de la venv existente. Sin instalaciones, sin servicios iniciados, sin Docker ni PostgreSQL reales.

| Verificacion | Resultado |
| --- | --- |
| Regresion antes del fix, detenida al primer fallo | 1 fallo esperado: la segunda liberacion devolvia ledger-2 en vez de None; 0.54 s |
| Focales despues del fix | 18 passed; 0.38 s |
| Relacionadas, incluidos indices estaticos | 232 passed, 1 warning; 30.92 s |
| Suite completa apps/api/tests | 1382 passed, 68 skipped, 1 warning; 157.40 s |
| Intentos bloqueados de conexiones en las tres ejecuciones verdes | 0 |
| Ruff check de los tres archivos Python afectados | PASS |
| Ruff format --check de las dos pruebas nuevas | PASS |
| git diff --check y diff --cached --check | PASS |
| secret-guard sobre los cinco archivos de codigo | Sin hallazgos |
| Comparacion del checkout original | Status y diff preservados |

El escaneo adicional de este reporte marco una sola coincidencia generica de alta entropia: el enlace publico a GitHub del commit base, en la linea 19. Se reviso manualmente como falso positivo, no una credencial. El escaneo de PRESENCIA-CODEX no tuvo hallazgos. No se cambio la configuracion del detector.

El warning es la deprecacion existente de httpx en TestClient. No se cambio ninguna dependencia. Las 68 pruebas omitidas no se cuentan como aprobadas; esta corrida no enumero sus motivos. No se validaron PostgreSQL real, aplicacion de indices, migraciones, imagen de despliegue ni servicios cloud.

El intercalado se reproduce con una conexion ficticia que ejecuta el metodo real de un competidor antes de devolver el bloqueo al segundo. No utiliza dos conexiones PostgreSQL ni demuestra la planificacion del motor real. Si existe autorizacion futura, falta la integracion aislada contra PostgreSQL antes de aplicar la migracion.

## Comandos y reproduccion local

Se invoco el Python existente con -B y un ejecutor temporal por entrada estandar. No debe ejecutarse pytest sin el aislamiento al reproducir esta evidencia. El ejecutor elimina variables heredadas de la app, desactiva plugins automaticos/notificaciones/watcher y bloquea PostgreSQL, Redis, DNS, sockets externos y procesos hijos. Solo permite el socketpair interno de asyncio en Windows. No registra argumentos, destinos ni valores privados.

Argumentos de pytest usados con ese ejecutor:

- Rojo y focal verde: -p no:cacheprovider apps/api/tests/test_credit_hold_idempotency.py -q --tb=short -x
- Relacionadas: -p no:cacheprovider apps/api/tests/test_credit_hold_idempotency.py apps/api/tests/test_credit_hold_migration_static.py apps/api/tests/test_ads_marketplace.py apps/api/tests/test_business_order_ops.py apps/api/tests/test_chat_disputes.py apps/api/tests/test_jobs_notifications.py apps/api/tests/test_job_order_transitions.py -q --tb=short -x
- Completa: -p no:cacheprovider apps/api/tests -q --tb=short -x

Ejecutable: C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe -B -
Directorio: worktree aislado indicado arriba.
SELECTION en el siguiente ejecutor es la lista de argumentos correspondiente, no una variable del sistema.

```python
import os, sys, socket, inspect
system = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP", "PATH") if key in os.environ}
os.environ.clear()
os.environ.update(system)
os.environ.update(APP_ENV="test", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", ORDER_NOTIFICATION_SENDER_ENABLED="false", ONCHAIN_CREDIT_WATCHER_ENABLED="false", DATABASE_URL="postgresql://test:test@127.0.0.1:1/test", REDIS_URL="redis://127.0.0.1:1/0")
import pytest, psycopg, redis
from collections import Counter
blocked = Counter()
current = {"test": "collection"}
def deny(category):
    def blocked_call(*args, **kwargs):
        blocked[(current["test"], category)] += 1
        raise RuntimeError("ISOLATED_TEST_CONNECTION_BLOCKED")
    return blocked_call
psycopg.connect = deny("postgres")
psycopg.Connection.connect = deny("postgres")
redis.Redis.execute_command = deny("redis")
socket.create_connection = deny("socket")
original_connect = socket.socket.connect
def guarded_connect(sock, address):
    if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
        if any(frame.function in ("socketpair", "_fallback_socketpair") and frame.filename.endswith("socket.py") for frame in inspect.stack()[1:5]):
            return original_connect(sock, address)
    return deny("socket")(sock, address)
socket.socket.connect = guarded_connect
def audit_guard(event, args):
    categories = {"socket.getaddrinfo": "dns", "socket.gethostbyname": "dns",
                  "socket.gethostbyaddr": "dns", "socket.sendto": "socket",
                  "socket.sendmsg": "socket", "subprocess.Popen": "process", "os.system": "process"}
    if event in categories:
        deny(categories[event])()
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            if any(frame.function in ("socketpair", "_fallback_socketpair")
                   and frame.filename.endswith("socket.py") for frame in inspect.stack()[1:8]):
                return
        deny("socket")()
sys.addaudithook(audit_guard)
class Guard:
    def pytest_sessionstart(self, session):
        self.session = session

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item):
        relative_path = item.path.relative_to(item.config.rootpath).as_posix()
        function = getattr(item, "originalname", None) or item.name.split("[", 1)[0]
        current["test"] = relative_path + "::" + function

    def pytest_runtest_logreport(self, report):
        if report.when == "teardown" and blocked:
            self.session.shouldstop = "ISOLATED_TEST_CONNECTION_BLOCKED"

code = pytest.main(SELECTION, plugins=[Guard()])
total = sum(blocked.values())
print("ISOLATION_BLOCKED_COUNT", total)
groups = sorted(blocked.items())
for (test, category), count in groups[:100]:
    print("ISOLATION_BLOCKED", test, category, count)
print("ISOLATION_GROUPS_SHOWN", min(len(groups), 100))
print("ISOLATION_GROUPS_OMITTED", max(0, len(groups) - 100))
sys.exit(code or (1 if total else 0))

```

Otros comandos ejecutados, siempre sobre rutas explicitas:

```text
ruff check --no-cache apps/api/app/modules/ads/postgres_credit_holds.py apps/api/tests/test_credit_hold_idempotency.py apps/api/tests/test_credit_hold_migration_static.py
ruff format --no-cache apps/api/tests/test_credit_hold_idempotency.py apps/api/tests/test_credit_hold_migration_static.py
ruff format --check --no-cache apps/api/tests/test_credit_hold_idempotency.py apps/api/tests/test_credit_hold_migration_static.py
git diff --check
git diff --cached --check
python -B <skill-secret-guard>/scripts/guard.py --files <los cinco archivos del commit>
git commit -m "fix: recheck credit hold movements after wallet lock"
```

## Migracion y despliegue: no ejecutados

La autorizacion del ciclo permite preparar codigo y SQL para revision, no ejecutar migraciones.

Procedimiento propuesto para una aprobacion posterior:

1. Revisar el cambio con Dilitan y probar la migracion y la concurrencia en PostgreSQL aislado con datos ficticios.
2. Con autorizacion especifica para el entorno destino, revisar duplicados de las tres claves e indices ya existentes, con salida acotada y sin publicar datos. Si hay duplicados, detenerse: no borrarlos ni reescribir el ledger automaticamente.
3. Planificar una ventana compatible con los bloqueos de CREATE UNIQUE INDEX y el tamano real de la tabla; no se asume costo o duracion.
4. Aplicar 0065 con el ejecutor transaccional existente bajo autorizacion y comprobar los tres indices. No se usa IF NOT EXISTS para ocultar un indice inesperado del mismo nombre.
5. Desplegar solo despues de esa validacion y de la aprobacion correspondiente. Los rechecks no dependen de ignorar conflictos, pero la proteccion adicional no existe hasta aplicar los indices.
6. Si se revierte el codigo, conservar inicialmente los indices y pausar nuevas mutaciones de creditos hasta evaluar compatibilidad. Volver al codigo anterior reabre el intervalo de carrera. Quitar los indices requiere aprobacion separada; la reversa no elimina movimientos ni restaura saldos.

## Publicacion y bloqueo actual

Comprobacion de despliegue indirecto previa a push:

- Workflows encontrados en la base: nodo-cloud-load-runner y nodo-connection-origin-probe, ambos workflow_dispatch; no se invocaron.
- Railway, consulta visual de solo lectura: nodo-api-staging / nodo-api muestra Source vacio, con Connect Repo / Connect Image. No tiene una fuente Git conectada. No se cambiaron configuraciones ni se abrieron variables.
- Cloudflare: el navegador de Codex llega al login. El Wrangler 4.130.0 ya instalado en cache, invocado directamente con pages project list y telemetria desactivada, tampoco pudo autenticar en modo no interactivo. Tuvo ademas un fallo de permiso al escribir su log local. No se instalaron herramientas, no se aportaron tokens ni se inicio un login automatico.
- Pendiente: acceso de Carlos a Cloudflare para consultar si el proyecto Pages tiene integracion Git y si esta rama dispararia previews. No cambiar configuracion para resolverlo sin autorizacion.

Por esa verificacion faltante no se hizo push ni PR. No es un bloqueo tecnico que corresponda resolver a Dilitan ni una nueva solicitud de aprobacion para programar. Codex conserva la correccion local y continuara la publicacion al poder demostrar el aislamiento.

## Entrega y siguiente accion

Este reporte se prepara como Markdown propio en la carpeta acordada; su subida y lectura posterior se comprueban antes de anunciarlo entregado. PRESENCIA-CODEX se actualiza para reemplazar el estado obsoleto del primer paquete. No se modifican instrucciones ni revisiones de Dilitan.

Siguiente accion de Codex: comprobar Cloudflare, publicar esta rama sin despliegue, verificar el SHA remoto y entregar el enlace exacto para revision. Luego esperar APROBADO u OBSERVACIONES de Dilitan antes de TAREA-001.

Sin migraciones ejecutadas, despliegues, cambios de proveedores, datos reales, secretos, bots, wallets, USDC ni cambios de permisos de administrador. No se declara NODO listo para produccion.
