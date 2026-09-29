# Integracion de cuatro paquetes revisados - NODO

Fecha: 2026-09-29, America/New_York.
Estado: VALIDACION_LOCAL_CONJUNTA_COMPLETA; PENDIENTE_REVISION_DILITAN.
Responsabilidades: Codex implementa y entrega evidencia; Dilitan revisa; Carlos autoriza integracion en ramas de despliegue, migraciones y produccion.

## Resumen y autorizacion

Carlos respondio "Dale" a preparar una rama de integracion con los cuatro paquetes aprobados y probarlos juntos, antes de llevarlos a main. Se creo esa rama, se integraron los cuatro historiales sin conflictos y se ejecutaron comprobaciones locales aisladas. No hubo correcciones manuales adicionales del producto ni cambios en pruebas para obtener resultados verdes.

Las cuatro revisiones individuales APROBADO siguen siendo evidencia historica, no equivalen a una aprobacion del conjunto ni del proyecto completo. Esta entrega solicita la revision conjunta de Dilitan. N9 (registro de IP y user-agent) permanece fuera por decision expresa de Carlos.

## Identidad verificable

- Repositorio existente: C:\Users\carlo\Documents\Playground\NODO.
- Checkout aislado reutilizado: C:\Users\carlo\Documents\Playground\NODO-credit-holds-review.
- Base: codex/review-automatic-order-transitions-20260928, SHA 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1.
- Rama: codex/integration-reviewed-fixes-20260929.
- Codigo integrado, probado y publicado: 50bcb67788d310ad3a5b7019338b13168ae8fbca.
- [PR #5 en borrador](https://github.com/Goldempire-coder/NODO/pull/5), dirigido a la rama base anterior, NO a main.
- [Rama de revision](https://github.com/Goldempire-coder/NODO/tree/codex/integration-reviewed-fixes-20260929).
- Este reporte se agrega en un commit exclusivamente documental posterior. Su SHA final se registra en PRESENCIA-CODEX.md y en la entrega; las cifras de pruebas corresponden al SHA de codigo anterior.
- main remoto observado: 74e6d2658dcd545a0d4d4d9aeba8263121a75499. No se modifica.

| Paquete aprobado | Rama | SHA remoto de entrada |
| --- | --- | --- |
| PR #1: idempotencia de reservas de creditos | codex/credit-hold-idempotency-20260928 | 43016571df21eeb1217dca6fd2ffabdf5c1a3b7f |
| PR #2: CORS y configuracion Telegram | codex/cors-telegram-config-20260928 | 574067a75938f858d3990d874a27b18776680df3 |
| PR #3: dominios permitidos y guia workers | codex/wallet-allowlist-20260928 | b525a39223e7ee5018b394fe3483f594c73f2532 |
| PR #4: ejemplos, simplificacion y auditoria | codex/hygiene-audit-20260929 | 0a5627fe05635b78301590bcaab404d073ef9009 |

PR #1 a #4 no se fusionaron ni cerraron en GitHub. Se partio del SHA exacto de PR #1 y se hicieron tres merges locales --no-ff de los otros SHA aprobados. Los cuatro son ancestros del candidato.

- Merge CORS: 84e4cf068c76ce5bec740b546d86575e9a67f584.
- Merge dominios: f21c610404df79561304fc858cf90cc1452ebd6f.
- Merge higiene: 50bcb67788d310ad3a5b7019338b13168ae8fbca.

## Revision de integracion y alcance

Contra la base, el candidato contiene 23 archivos, 1834 inserciones y 22 eliminaciones, antes de agregar este reporte. Los 22 archivos exclusivos de un paquete se compararon por objeto Git: contenido identico al SHA aprobado correspondiente. El unico archivo compartido, .env.example, integra 24 lineas agregadas de los tres paquetes que lo modificaban; se reviso el diff combinado. No se perdieron sus cambios ni se agregaron valores de credenciales. No hay rutas inesperadas.

Archivos del candidato:
- .env.example
- .env.staging.example
- apps/api/app/core/config.py
- apps/api/app/main.py
- apps/api/app/modules/ads/postgres_credit_holds.py
- apps/api/app/modules/jobs/service.py
- apps/api/app/modules/orders/payment_reporting.py
- apps/api/tests/test_business_wallet_probe_static.py
- apps/api/tests/test_cors_telegram_config.py
- apps/api/tests/test_credit_hold_idempotency.py
- apps/api/tests/test_credit_hold_migration_static.py
- apps/api/tests/test_hygiene_audit.py
- apps/web/next.config.mjs
- apps/web/src/lib/env.ts
- apps/web/src/lib/wallet/metamaskHandoff.ts
- database/migrations/0065_credit_hold_idempotency.down.sql
- database/migrations/0065_credit_hold_idempotency.up.sql
- governance/owner_reviews/REPORTE-2026-09-28-cors-telegram.md
- governance/owner_reviews/REPORTE-2026-09-28-credit-holds.md
- governance/owner_reviews/REPORTE-2026-09-28-wallet-workers.md
- governance/owner_reviews/REPORTE-2026-09-29-higiene.md
- operations/sops/DEPLOYMENT_SOP.md
- scripts/test_wallet_allowlist.cjs

A esa lista se agrega solamente governance/owner_reviews/REPORTE-2026-09-29-integracion-cuatro-paquetes.md. La presencia es un archivo de coordinacion local/Drive, no un cambio de producto.

Se preservaron los cambios rastreados originales en apps/web/src/app/globals.css, apps/web/src/app/website/page.tsx y operations/README.md, y los archivos locales ajenos, incluido el laboratorio de respaldos. El diff binario rastreado original se comparo antes de publicar; permanece identico. El checkout de integracion estaba limpio antes de preparar este reporte.

## Resultados nuevos de este ciclo

| Comprobacion | Resultado observado |
| --- | --- |
| pytest relacionadas, 11 archivos | 233 passed, 1 warning, 18.79 s, salida 0 |
| pytest completa | 1433 passed, 68 skipped, 1 warning, 150.60 s, salida 0 |
| Guardia de conexiones en ambas ejecuciones | ISOLATION_BLOCKED_COUNT 0; cero grupos |
| Casos JS de dominios con datos ficticios | 67 passed, blocked=0 |
| Typecheck frontend, TypeScript 5.9.3 | 211 archivos raiz, 0 diagnosticos |
| Ruff check de cinco pruebas y dos modulos indicados abajo | All checks passed |
| Ruff format --check de las cinco pruebas | 5 files already formatted |
| git diff --check contra la base | Salida 0 |
| Escaner de secretos, 19 archivos no historicos del candidato | 3 avisos genericos de entropia, revisados como falsos positivos |

Las 68 omisiones se mantuvieron, no cuentan como pruebas aprobadas ni se redujeron controles. El unico aviso es la deprecacion previa de httpx en Starlette TestClient. No se instalo su alternativa ni se alteraron dependencias.

Los tres avisos del escaner corresponden a nombres estaticos de buckets ya presentes en las plantillas, lineas 108-110 de .env.staging.example: business-verification, payment-evidence y credit-purchase-proofs. No son credenciales. No se modifico ninguna lista de excepciones. El escaneo automatico aislado devolvio 1 por esos avisos; no se presenta como una salida verde automatica. Los cuatro reportes historicos conservan exactamente los blobs previamente revisados. El escaneo separado de este reporte dio un aviso generico en la linea 61: la ruta del reporte historico de creditos, cotejada como nombre de archivo y no como secreto. Se reviso tambien el texto nuevo antes del commit.

Se mantienen los avisos de formato preexistentes documentados en config/main y payment_reporting. No se afirma que un lint global del proyecto este limpio; la integracion no introduce modificaciones en esos blobs respecto a los aprobados.

## Reproduccion de las comprobaciones locales

Comandos ejecutados desde el checkout aislado. Se reutilizaron Python, Node, TypeScript, pytest y Ruff ya instalados; sin instalaciones, descargas o inicio de servicios. No ejecutar la suite sin las guardias descritas.

### Python: ejecutor temporal en memoria

Se envio el bloque siguiente por stdin, mediante un here-string de PowerShell, a:

```powershell
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -
```

SELECTION se sustituyo antes de enviar el bloque. Para las relacionadas:

```python
SELECTION = [
    "apps/api/tests/test_credit_hold_idempotency.py",
    "apps/api/tests/test_credit_hold_migration_static.py",
    "apps/api/tests/test_cors_telegram_config.py",
    "apps/api/tests/test_business_wallet_probe_static.py",
    "apps/api/tests/test_business_credit_handoff_static.py",
    "apps/api/tests/test_auth_lifecycle_static.py",
    "apps/api/tests/test_hygiene_audit.py",
    "apps/api/tests/test_jobs_notifications.py",
    "apps/api/tests/test_payment_instructions_reports.py",
    "apps/api/tests/test_logging_output.py",
    "apps/api/tests/test_backend_observability_foundation.py",
    "-q",
    "--tb=short",
    "-x",
    "-p",
    "no:cacheprovider"
]
```

Para la suite completa:

```python
SELECTION = ["apps/api/tests", "-q", "--tb=short", "-x", "-p", "no:cacheprovider"]
```

Bloque utilizado:

```python
import os, sys, socket, inspect
system = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP", "PATH") if key in os.environ}
os.environ.clear()
os.environ.update(system)
os.environ.update(APP_ENV="test", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", ORDER_NOTIFICATION_SENDER_ENABLED="false", ONCHAIN_CREDIT_WATCHER_ENABLED="false", DATABASE_URL="postgresql://test:test@127.0.0.1:1/test", REDIS_URL="redis://127.0.0.1:1/0")
sys.path[:0] = ["apps/api", "apps/api/tests"]
import tempfile
os.environ["PYTEST_DEBUG_TEMPROOT"] = tempfile.mkdtemp(prefix="nodo-integration-tests-")
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

Se limpia el entorno heredado, se usan direcciones ficticias, se deshabilitan emisores y se bloquean PostgreSQL, Redis, DNS, sockets y procesos externos. La unica excepcion de socket es el par interno de la biblioteca estandar necesario para el bucle asincrono, no un servicio. Cada invocacion usa un directorio temporal nuevo con datos de prueba; no se borraron datos ni cambiaron permisos. Un intento bloqueado mantiene el fallo aunque una prueba capture la excepcion; el ejecutor corta tras esa prueba y nunca registra argumentos o destinos.

### JS de dominios y typecheck

```powershell
& 'C:\Program Files\nodejs\node.exe' --permission --allow-fs-read='C:\Users\carlo\Documents\Playground\NODO-credit-holds-review' --allow-fs-read='C:\Users\carlo\Documents\Playground\NODO\node_modules' --allow-fs-read='C:\Users\carlo\Documents\Playground\NODO\apps\web\node_modules' scripts/test_wallet_allowlist.cjs 'C:\Users\carlo\Documents\Playground\NODO\apps\web\node_modules\typescript'
```

El script revisado limpia el entorno, bloquea red/procesos y usa un navegador y Telegram ficticios; no conecta ninguna wallet.

Para typecheck se uso el mismo Node y permisos de lectura, pasando por stdin (argumento - en lugar del script de pruebas) el siguiente bloque. Los imports relativos se resuelven contra el checkout integrado y solo las dependencias instaladas se toman del repositorio original. No emite compilados ni archivos incrementales:

```javascript
const path=require("node:path");
for(const key of Object.keys(process.env)) delete process.env[key];
const ts=require("C:/Users/carlo/Documents/Playground/NODO/apps/web/node_modules/typescript");
const root=process.cwd(), original="C:/Users/carlo/Documents/Playground/NODO";
const file=path.join(root,"apps/web/tsconfig.json");
const conf=ts.readConfigFile(file,ts.sys.readFile);
const parsed=ts.parseJsonConfigFileContent(conf.config,ts.sys,path.dirname(file));
const options={...parsed.options,incremental:false,noEmit:true,typeRoots:[path.join(original,"apps/web/node_modules/@types")]};
const host=ts.createCompilerHost(options);
host.resolveModuleNames=(names,containing)=>names.map(name=>{
 const local=ts.resolveModuleName(name,containing,options,host).resolvedModule;
 if(local||name.startsWith(".")) return local;
 return ts.resolveModuleName(name,path.join(original,path.relative(root,containing)),options,host).resolvedModule;
});
host.resolveTypeReferenceDirectives=(names,containing)=>names.map(value=>{
 const name=typeof value==="string"?value:value.fileName;
 return ts.resolveTypeReferenceDirective(name,containing,options,host).resolvedTypeReferenceDirective ||
 ts.resolveTypeReferenceDirective(name,path.join(original,path.relative(root,containing)),options,host).resolvedTypeReferenceDirective;
});
const program=ts.createProgram(parsed.fileNames,options,host);
const errors=[...parsed.errors,...ts.getPreEmitDiagnostics(program)];
for(const d of errors.slice(0,20)) console.log("TS",d.code,d.file?path.relative(root,d.file.fileName):"",ts.flattenDiagnosticMessageText(d.messageText," "));
console.log("TYPECHECK",errors.length,"rootFiles",parsed.fileNames.length,"typescript",ts.version);
process.exit(errors.length?1:0);
```

### Formato, diff y revision de secretos

```powershell
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff check --no-cache apps/api/tests/test_credit_hold_idempotency.py apps/api/tests/test_credit_hold_migration_static.py apps/api/tests/test_cors_telegram_config.py apps/api/tests/test_business_wallet_probe_static.py apps/api/tests/test_hygiene_audit.py apps/api/app/modules/jobs/service.py apps/api/app/modules/ads/postgres_credit_holds.py
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff format --check --no-cache apps/api/tests/test_credit_hold_idempotency.py apps/api/tests/test_credit_hold_migration_static.py apps/api/tests/test_cors_telegram_config.py apps/api/tests/test_business_wallet_probe_static.py apps/api/tests/test_hygiene_audit.py
& 'C:\Program Files\Git\cmd\git.exe' -c safe.directory=C:/Users/carlo/Documents/Playground/NODO-credit-holds-review diff --check 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1 HEAD
```

El helper local C:\Users\carlo\.codex\skills\secret-guard\scripts\guard.py se ejecuto con --format md --files y los 19 archivos del candidato excluyendo los cuatro reportes historicos. Se inspecciono el diff y cada aviso sin exponer valores privados. Las comprobaciones de contenido usaron git rev-parse SHA:ruta por cada archivo exclusivo y git merge-base --is-ancestor por cada SHA de entrada.

## Publicacion sin despliegue

Antes de publicar se verifico en solo lectura:
- Cloudflare nodo-staging: No Git connection.
- Railway nodo-api-staging, servicio nodo-api: Source vacio, opciones Connect Repo/Connect Image.
- Los dos workflows del repositorio tienen workflow_dispatch; no se invocaron.
- Sin core.hooksPath configurado y solo hooks .sample.

Se subio unicamente codex/integration-reviewed-fixes-20260929. No se cambio main, la rama base ni los cuatro heads de entrada. No se aplicaron configuraciones cloud, limites, planes ni recursos nuevos. No se ejecuto un deploy directo o indirecto en las rutas comprobadas. El PR es borrador y no fue fusionado. El reporte Markdown y la presencia se entregan en la carpeta acordada y se cotejan por lectura; no se editan tareas ni revisiones de Dilitan.

## Limites, costos y proxima decision

- No se ejecuto la migracion 0065 ni su rollback. Sus pruebas son estaticas y con dobles, no demuestran concurrencia ni compatibilidad con una base PostgreSQL real.
- No hubo conexiones a PostgreSQL/Redis, bots, MetaMask, R2, Supabase o datos reales.
- No hubo build completo de Next ni ensayo visual en navegador/Telegram. El typecheck y los casos ficticios no sustituyen esos controles.
- No se inicio infraestructura ni se contrataron recursos. No se midieron carga/capacidad ni costos de operacion futuros. Se conservan las consideraciones de consulta extra para revalidar reservas y datos de auditoria de los reportes individuales.
- No se agregaron registros de IP o user-agent; N9 sigue excluida.
- No se declara validado un respaldo ni NODO listo para produccion.

Siguiente paso: Dilitan revisa PR #5 contra la base y el SHA integrado exactos y deja su dictamen. Codex atiende bugs confirmados de esa revision antes de otra tarea. La autorizacion de Carlos para fusionar en una rama de despliegue, los ensayos aislados de PostgreSQL/migracion y la liberacion posterior permanecen separados. No hay cierre global del proyecto ni autorizacion implicita de produccion.
