# Reporte Codex - TAREA-003: higiene y auditoria

Fecha: 2026-09-29, America/New_York.
Estado: IMPLEMENTADO Y VALIDADO LOCALMENTE; ESPERA REVISION DE DILITAN.
Codex construye; Dilitan revisa; Carlos decide integracion, despliegue y alcance.

## Resumen
- N4: ejemplos backend completados con valores vacios; ninguna credencial real.
- N6: eliminado fallback redundante del identificador de orden, sin cambiar respuestas.
- N7: auditoria registra la fecha efectiva de la simulacion, sin cambiar reglas ni reintentos.
- N9: expresamente excluido por Carlos; no se agregan IP ni user-agent a logs.
- 21 casos nuevos, 134 pruebas relacionadas y suite final 1381 passed / 68 skipped / 1 warning. Sin conexiones reales.

## Entrega e identidad

- Repositorio existente: C:\Users\carlo\Documents\Playground\NODO; no clonado ni sustituido.
- Worktree limpio reutilizado: C:\Users\carlo\Documents\Playground\NODO-credit-holds-review.
- Base verificada local/remota: `6069a75ee2fa6f9b05fdf21ebbfc77039af562c1`.
- Base del PR: `codex/review-automatic-order-transitions-20260928`, no main.
- Rama: [codex/hygiene-audit-20260929](https://github.com/Goldempire-coder/NODO/tree/codex/hygiene-audit-20260929).
- Codigo probado y publicado: `7152961458ae45d5766708ca7f6d303ee3f0eb70`.
- [PR #4 en borrador](https://github.com/Goldempire-coder/NODO/pull/4), sin fusionar.
- El commit documental posterior solo incorpora este reporte; PRESENCIA registra su SHA final.
- Esta rama no integra ni reemplaza PR #1, #2 o #3. Sus pruebas adicionales no forman parte del total de esta base.

## Autorizacion y revision anterior

Leida [REVISION-2026-09-28-wallet-workers.md](https://drive.google.com/file/d/1TPANsKSyFuLEBnwFeRErcIsGE5nACrmJ/view), modificada 2026-09-29T04:00:13.330Z: APROBADO de TAREA-002, codigo c877805eb9afcef129e55ef76cdcefb7611ce410, PR #3. Dilitan reviso diff y evidencia, sin ejecutar su propia suite; no se presenta como otra ejecucion.

Leida TAREA-003 v2, ID 1-xYrWLV_P8ulMGtyLkHsDIqFynMaEBCe, y gobernanza de piloto, seguridad de jobs y ENGINEERING_GUARDRAILS. Las instrucciones de Drive no amplian la autorizacion de Carlos. No se clono ni se uso la rama nodo/fase-higiene sugerida; se mantiene el prefijo de revision codex/ y la base acordada.

Carlos respondio en este ciclo: **"Dejar las IP fuera y avanzar con lo demas"**. N9 sale de esta entrega por decision del Owner; no se solicita que Dilitan lo implemente ni se deja como bug pendiente. Cualquier futura captura de IP requiere una propuesta y aprobacion separadas.

## Comprobacion y cambios

### N4: ejemplos, no configuracion real
- `.env.example` es general/local (`APP_ENV=local`), no un ejemplo exclusivamente productivo.
- Agregados `SUPABASE_SERVICE_ROLE_KEY=` y `BASE_RPC_API_KEY=` donde faltaban.
- Agregado tambien `SUPABASE_URL=` en el ejemplo general porque `validate_env()` exige ambos campos cuando `PRIVATE_STORAGE_MODE=supabase`. El modo por defecto no cambia.
- Staging ya tenia la clave de servicio; no se duplica.
- `BASE_RPC_API_KEY` se lee como setting y se considera secreto, pero no se encontro un consumidor de ese setting en las llamadas RPC actuales. El comentario lo deja reservado y vacio; las llamadas usan `BASE_RPC_URL`. No se inventa una nueva integracion ni se afirma un fallo silencioso.
- Los nuevos valores quedan vacios y backend-only, sin prefijo NEXT_PUBLIC_. No se leen archivos .env reales ni paneles de secretos.

### N6: limpieza equivalente
- `require_uuid` devuelve una cadena UUID normalizada o lanza ApiError ante un valor no valido. Tambien admite None y devuelve None, pero el order_id de esta ruta es str; incluso con None, el fallback no aportaba un valor distinto.
- Se quita solo `or order_id`. No cambia require_uuid, la ruta, los permisos, idempotencia, estado o pago.
- Casos nuevos comprueban tres IDs no validos: 404 ORDER_NOT_FOUND y sin nuevo evento de auditoria. Las pruebas relacionadas conservan los flujos validos, ownership, idempotencia y carreras existentes.

### N7: fecha efectiva en auditoria
- El worker fija `now = current_time or utc_now()` una vez y lo conserva en `job_run.started_at`, incluidos los resultados de fallo y lock no adquirido.
- El servicio agrega `metadata_json.current_time = result["job_run"]["started_at"]` al evento existente `job_dry_run_executed`.
- No se recalcula el reloj ni se cambia el payload de idempotencia. El replay conserva el resultado y no duplica auditoria.
- No se impone ventana de +/-7 dias ni validacion nueva. No se cambia fecha, estado, orden, credito, notificacion o permiso.
- La propuesta de limitar fechas queda fuera: un dry-run administrativo puede necesitar simular fechas lejanas; cualquier restriccion nueva requiere decision de producto. Los tests preservan +/-30 dias y offsets.
- Se prueba el worker real con repositorios en memoria, incluyendo fallo ficticio, lock ocupado, admin/super_admin, denegaciones, clave obligatoria y comparacion exacta de metadata para no agregar contenido privado.

## Archivos incluidos

1. `.env.example`
2. `.env.staging.example`
3. `apps/api/app/modules/jobs/service.py`
4. `apps/api/app/modules/orders/payment_reporting.py`
5. `apps/api/tests/test_hygiene_audit.py` (nuevo, 21 casos)
6. `governance/owner_reviews/REPORTE-2026-09-29-higiene.md`

PRESENCIA-CODEX.md se actualiza como archivo propio de coordinacion local/Drive, no se mezcla en el commit de codigo. Sin cambios en website, frontend, observability.py, logging.py, laboratorio de respaldos o trabajo ajeno.

## Resultados nuevos

| Comprobacion | Resultado |
| --- | --- |
| Reproduccion antes del fix | 1 failed esperado: falta current_time; 2.14 s; 0 conexiones |
| Casos nuevos | 21 passed, 1 warning; 6.45 s; 0 conexiones |
| Relacionadas | 134 passed, 1 warning; 20.47 s; 0 conexiones |
| Primera suite | 592 passed, 1 skipped, 1 warning, 1 error de permisos; 69.02 s |
| Grupo afectado con temporal exclusivo | 13 passed; 0.13 s; 0 conexiones |
| Suite completa final | 1381 passed, 68 skipped, 1 warning; 152.40 s; 0 conexiones |
| Ruff test nuevo + jobs/service.py | All checks passed |
| Ruff format test nuevo | 1 file already formatted |
| Ruff payment_reporting.py | I001 preexistente, identico al leer archivo en SHA base; no se reformatea fuera de alcance |
| git diff --check / staged check | Sin errores |
| secret-guard, 5 archivos | Tres avisos genericos preexistentes en definiciones de buckets del ejemplo staging, revisados como falsos positivos |

Las 68 omisiones no son validaciones ni pruebas nuevas omitidas. No se cambiaron marcadores ni condiciones de fallo. El aviso de Starlette/TestClient sobre httpx era previo; no se instalaron dependencias para ocultarlo.

### Incidente de temporales
La primera suite se detuvo al crear tmp_path en `pytest-of-unknown`: WinError 5 por permisos de una carpeta temporal anterior. No fallo una expectativa funcional del producto. No se repitio el intento contra esa carpeta, se cambiaron permisos o se borro contenido. El ejecutor temporal posterior usa `tempfile.mkdtemp(prefix="nodo-hygiene-tests-")` y PYTEST_DEBUG_TEMPROOT para aislar los archivos ficticios en una carpeta nueva por invocacion. Se verifico primero el grupo de 13 pruebas y despues la suite completa. No se modifico codigo de pruebas existentes ni se salteo el caso fallido.

### Secretos y revision
Los tres avisos del escaner completo son las lineas 108-110 del ejemplo staging, nombres SUPABASE_STORAGE_BUCKET_* y sus nombres de buckets de ejemplo existentes. No son claves ni se modificaron. No se amplio la allowlist del escaner. El diff contiene exclusivamente campos vacios y datos ficticios; no se leyeron secretos. El escaner del reporte produjo dos avisos genericos adicionales (lineas 28 y 30): el enlace a la revision y el ID de TAREA-003 en Drive. Se cotejaron con los archivos leidos; no son credenciales.

Revision local del diff: sin hallazgos bloqueantes nuevos. Arquitectura, permisos, idempotencia y estados conservados. Sin nueva query, llamada externa o evento de auditoria; solo se agrega una cadena de fecha al evento ya escrito. Coste marginal: unos bytes por simulacion administrativa; ningun recurso, servicio o cargo cloud nuevo. No se declara capacidad ni precio para produccion. El reporte no sustituye la revision de Dilitan.

## Comandos reproducibles

Directorio de trabajo: `C:\Users\carlo\Documents\Playground\NODO-credit-holds-review`.
Runtime existente: `C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe`.
No instalar ni ejecutar la suite sin el aislamiento. El helper siguiente se envio por stdin, no se agrego como archivo del producto. Conserva entorno ficticio, bloqueo DB/Redis/red/subprocesos, salida fallida si hay intento bloqueado y diagnostico limitado a prueba/categoria. Socketpair local interno de Python se permite solo con comprobacion de pila.

Ejecutor final exacto (PowerShell):

```powershell
@'
import os, sys, socket, inspect
system = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP", "PATH") if key in os.environ}
os.environ.clear()
os.environ.update(system)
os.environ.update(APP_ENV="test", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", ORDER_NOTIFICATION_SENDER_ENABLED="false", ONCHAIN_CREDIT_WATCHER_ENABLED="false", DATABASE_URL="postgresql://test:test@127.0.0.1:1/test", REDIS_URL="redis://127.0.0.1:1/0")
sys.path[:0] = ["apps/api", "apps/api/tests"]
import tempfile
os.environ["PYTEST_DEBUG_TEMPROOT"] = tempfile.mkdtemp(prefix="nodo-hygiene-tests-")
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

code = pytest.main(["apps/api/tests","-q","--tb=short","-x","-p","no:cacheprovider"], plugins=[Guard()])
total = sum(blocked.values())
print("ISOLATION_BLOCKED_COUNT", total)
groups = sorted(blocked.items())
for (test, category), count in groups[:100]:
    print("ISOLATION_BLOCKED", test, category, count)
print("ISOLATION_GROUPS_SHOWN", min(len(groups), 100))
print("ISOLATION_GROUPS_OMITTED", max(0, len(groups) - 100))
sys.exit(code or (1 if total else 0))

'@ | & 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -
```

Para reproducir las selecciones focales/relacionadas, sustituir solo la lista de pytest.main manteniendo todos los controles. Las dos ejecuciones iniciales precedieron a la linea de temporal exclusivo:
- Focales: `["apps/api/tests/test_hygiene_audit.py", "-q", "--tb=short", "-x", "-p", "no:cacheprovider"]`.
- Relacionadas: `["apps/api/tests/test_hygiene_audit.py", "apps/api/tests/test_jobs_notifications.py", "apps/api/tests/test_payment_instructions_reports.py", "apps/api/tests/test_logging_output.py", "apps/api/tests/test_backend_observability_foundation.py", "-q", "--tb=short", "-x", "-p", "no:cacheprovider"]`.
- Temporal: `["apps/api/tests/test_cloudflare_pages_staging_deploy_guard.py", "-q", "--tb=short", "-x", "-p", "no:cacheprovider"]`.

```powershell
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff check apps/api/tests/test_hygiene_audit.py apps/api/app/modules/jobs/service.py
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff format --check apps/api/tests/test_hygiene_audit.py
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff check apps/api/app/modules/orders/payment_reporting.py
& 'C:\Program Files\Git\cmd\git.exe' -c safe.directory=C:/Users/carlo/Documents/Playground/NODO-credit-holds-review show 6069a75:apps/api/app/modules/orders/payment_reporting.py | & 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff check --stdin-filename apps/api/app/modules/orders/payment_reporting.py -
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B 'C:\Users\carlo\.codex\skills\secret-guard\scripts\guard.py' --files .env.example .env.staging.example apps/api/app/modules/jobs/service.py apps/api/app/modules/orders/payment_reporting.py apps/api/tests/test_hygiene_audit.py --format json
& 'C:\Program Files\Git\cmd\git.exe' -c safe.directory=C:/Users/carlo/Documents/Playground/NODO-credit-holds-review diff --check
```

## Publicacion y limites

Antes del push se comprobaron en solo lectura Cloudflare nodo-staging: No Git connection; Railway nodo-api-staging/nodo-api: Source vacio, Connect Repo/Connect Image. Los dos workflows existentes son workflow_dispatch; no se invocaron. No se modificaron proveedores ni su configuracion. El entorno llamado production dentro del proyecto staging no se presenta como produccion separada.

No merge, force-push, deploy, migraciones, instalaciones, servicios reales, bots, wallets, USDC, datos reales ni credenciales. No se leyeron paneles Variables. Git usa safe.directory por comando para el worktree conocido, sin cambiar configuracion global.

Pendientes generales que esta entrega no resuelve:
- Dilitan debe revisar TAREA-003 / PR #4 antes de otra tarea.
- Integracion de PR #1/#2/#3/#4 requiere aprobacion de Carlos y pruebas conjuntas.
- PostgreSQL aislado y migracion 0065 requieren su aprobacion/evidencia separada.
- Dominio productivo y configuracion de despliegue siguen pendientes de autorizacion.
- No se ejecutaron nuevas pruebas reales de Telegram, MetaMask, pagos, DB/Redis, storage, produccion o recuperacion.
- No hay revision final explicita del proyecto integrado: no se cierra el ciclo ni se declara produccion lista.
