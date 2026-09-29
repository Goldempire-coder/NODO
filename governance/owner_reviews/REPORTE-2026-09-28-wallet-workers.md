# NODO - TAREA-002: dominios MetaMask y dimensionamiento

Fecha: 2026-09-28 (America/New_York).
Estado: ENTREGADO PARA REVISION DE DILITAN; sin merge ni deploy.
Codex implementa; Dilitan revisa; Carlos decide integracion y produccion.

## Resumen

- Lista publica configurable de origenes HTTPS para ambos enlaces MetaMask.
- Produccion sin configuracion rechaza; staging sigue funcionando en ambientes de prueba.
- Se conservan validacion del token, privacidad y navegacion existente; el rechazo muestra un mensaje comprensible.
- Agregados 67 casos ejecutables ficticios y guia de dimensionamiento sin cambiar recursos.
- Pendiente revision de Dilitan y validacion de release posterior; no es aprobacion de produccion.

## Autorizacion y trazabilidad

El diagnostico anterior detuvo TAREA-002 por la exclusion de wallets del ciclo automatico. Carlos respondio "dale" a la pregunta explicita de autorizar solo esta lista y pruebas ficticias, sin conectar carteras, mover dinero ni desplegar. Esa autorizacion permite esta correccion local, no configurar wallets reales ni activar pagos.

- [TAREA-002 v2](https://drive.google.com/file/d/1CUjFMxgxN1mOozB2UnU0Ba3fiSQ6aP-B/view).
- [APROBADO de TAREA-001](https://drive.google.com/file/d/1D0IeCAoWT_3gevS59eTpMdP0q7l84Fwo/view), leido antes de comenzar. Dilitan hizo revision estatica, no ejecuto la suite.
- Base exacta: 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1.
- Rama: [codex/wallet-allowlist-20260928](https://github.com/Goldempire-coder/NODO/tree/codex/wallet-allowlist-20260928).
- Codigo probado y publicado: [c877805eb9afcef129e55ef76cdcefb7611ce410](https://github.com/Goldempire-coder/NODO/commit/c877805eb9afcef129e55ef76cdcefb7611ce410).
- [PR #3 en borrador](https://github.com/Goldempire-coder/NODO/pull/3), base codex/review-automatic-order-transitions-20260928, no main.
- El commit documental posterior contiene este reporte, sin alterar el codigo probado. Su SHA final se registra en PRESENCIA-CODEX.md tras verificar el push.
- Worktree reutilizado: C:\Users\carlo\Documents\Playground\NODO-credit-holds-review. Estaba limpio en 574067a antes de crear la rama desde 6069a75; no se clono ni reemplazo NODO.
- Esta rama no incluye ni reemplaza PR #1 (creditos) o PR #2 (CORS/Telegram). La futura integracion requiere aprobacion y pruebas conjuntas.
- Gobernanza releida: SOURCE_OF_TRUTH.md, DO_NOT_INVENT.md y ENGINEERING_GUARDRAILS.md. Se preservan limites operativos y Base Sepolia; no se autoriza dinero real.

## Hallazgo contrastado

La lista fija de metamaskHandoff.ts protegia tanto buildMetaMaskWalletProbeDeeplink como buildMetaMaskCreditHandoffDeeplink. Un origen HTTPS productivo distinto de staging no podia abrir ninguno. useBusinessCreditsModel ya captura el error y lo presenta: no se confirmo un crash silencioso de toda la app.

La prueba estatica anterior exigia literalmente staging. Se actualizo esa expectativa para la politica autorizada, conservando controles de credenciales, rutas, query, fragmentos, loopback y privacidad. No se borraron pruebas para ocultar un fallo.

## Archivos incluidos

1. apps/web/src/lib/wallet/metamaskHandoff.ts: configuracion por ambiente, validacion estricta, rechazo acotado.
2. apps/web/src/lib/env.ts: lectura estatica de NEXT_PUBLIC_WALLET_ALLOWLIST.
3. apps/web/next.config.mjs: exportacion explicita de esa configuracion publica.
4. .env.example: plantilla comentada y limites; no se toca ningun .env real.
5. apps/api/tests/test_business_wallet_probe_static.py: una expectativa actualizada, el resto conservado; ajuste de comillas equivalente por formato.
6. scripts/test_wallet_allowlist.cjs: 67 casos comportamentales con TypeScript existente, datos y ventanas ficticios.
7. operations/sops/DEPLOYMENT_SOP.md: guia breve de workers, CPU/memoria, replicas y pool.
8. governance/owner_reviews/REPORTE-2026-09-28-wallet-workers.md: este reporte.

PRESENCIA-CODEX.md se actualiza solo en el checkout original y Drive, no se mezcla con codigo. Website, operations/README.md y laboratorio de respaldos permanecen fuera del commit; el diff binario rastreado del checkout original se verifico identico al anterior.

## Politica implementada

- NEXT_PUBLIC_WALLET_ALLOWLIST es CSV publico de origenes HTTPS exactos, sin wildcard, credenciales, ruta extra, query, fragmento, espacios internos ni barra invertida. Una entrada invalida invalida toda la lista.
- Se normalizan host, puerto estandar y slash final con URL; puerto no estandar y subdominio requieren coincidencia explicita. Se rechazan rutas con segmentos colapsables, incluso si URL las normaliza a raiz.
- NEXT_PUBLIC_APP_ENV distingue produccion de staging, aunque NODE_ENV sea production en ambos builds.
- Solo local/dev/development/staging/test conservan staging por defecto; next dev sin APP_ENV tambien conserva ese comportamiento. Ambiente desconocido o ausente en build productivo no hereda staging.
- Produccion vacia deniega; produccion rechaza staging y sus subdominios aun si aparecen en el CSV. HTTP loopback queda solo en ambientes no productivos. Una lista explicita reemplaza el default HTTPS, no agrega cualquier host.
- El error mantiene un codigo estable en la propiedad code y registra solo ese codigo fijo en console.warn. El mensaje es "No se puede abrir MetaMask desde este sitio. Contacta a Soporte NODO." Nunca se imprimen origin, token, URL completa ni valores del entorno.
- No cambia proveedor, red, contrato, direccion receptora, firmas, permisos de gasto, importes, saldos, backend ni estado de pagos. El formato de token y los caminos de navegacion/retorno siguen intactos.
- La lista es una barrera de navegacion frontend, no reemplaza la autorizacion backend.

Next.js incorpora NEXT_PUBLIC al construir el bundle, no en el navegador por lectura dinamica; se mantiene el switch de accesos estaticos existente. Cambiar la lista desplegada requerira un build posterior autorizado. [Documentacion oficial Next.js 15](https://nextjs.org/docs/15/app/guides/environment-variables).

## Dimensionamiento sin cambios operativos

La guia sigue DB_POOL_SATURATION_RUNBOOK.md y conserva WEB_CONCURRENCY=1. Calcula replicas x workers x pool maximo, agrega otros consumidores y reserva, incluye replicas transitorias y diferencia clientes del pooler frente a conexiones PostgreSQL. CPU y memoria requieren mediciones; el ejemplo 60/10/10 conexiones y 1 GB es ficticio, no capacidad comprobada de los proveedores. No se cambian workers, limites, plan ni servicios.

## Resultados nuevos

| Comprobacion | Resultado |
| --- | --- |
| Regresion roja sobre helper de la base | Primer caso de dominio productivo configurado falla, 0 aprobados, 0 conexiones bloqueadas |
| Primer verde parcial | 60 casos pasaron; fallo del ejecutor al cargar next.config.mjs como CommonJS. Se detuvo esa ejecucion |
| Correccion del ejecutor | Se transpila ese modulo con nombre TS virtual; no se sustituye ni omite su contenido. Luego se agregaron casos de normalizacion de rutas |
| Regresion JS final | 67 passed; blocked=0; Node v24.19.0; TypeScript 5.9.3 ya instalado |
| Pruebas Python relacionadas | 47 passed en 0.42 s; 0 intentos bloqueados |
| Suite Python completa | 1360 passed, 68 skipped, 1 warning en 149.35 s; 0 intentos bloqueados |
| Tipos frontend | 211 archivos raiz, 0 diagnosticos; TypeScript 5.9.3, noEmit |
| Ruff check y format finales del test modificado | Ambos exit 0 |
| Diff y escaner de los 7 archivos de implementacion | diff --check exit 0; secret-guard [] exit 0 |

Los 1360 no son una disminucion de cobertura del mismo codigo: esta rama parte de 6069a75 y no contiene los 22 tests de PR #1 ni los 30 de PR #2. Los 67 casos JS se ejecutan por separado, no estan sumados al total pytest.

El aviso existente es StarletteDeprecationWarning por httpx/TestClient. No se instalo httpx2 ni se oculto el aviso. Los 68 skips no se consideran aprobados ni se usaron para afirmar produccion. Un primer control de formato pidio acortar el nombre nuevo del test y ajustar comillas equivalentes; se corrigio y la suite completa se ejecuto despues.

## Comandos y aislamiento

Directorio de trabajo para las pruebas:
C:\Users\carlo\Documents\Playground\NODO-credit-holds-review

No se instalaron dependencias. El test JS carga unicamente helper/env/theme/config revisados, con process.env ficticio en su contexto y ventana/Telegram simulados. Bloquea carga de modulos de red/subprocesos y fetch, y usa permisos Node de lectura acotada sin permisos de escritura o procesos hijos. node:vm aqui separa fixtures, NO se presenta como una frontera para codigo hostil. [Documentacion oficial Node](https://nodejs.org/api/vm.html).

~~~powershell
& 'C:\Program Files\nodejs\node.exe' --permission --allow-fs-read='C:\Users\carlo\Documents\Playground\NODO-credit-holds-review' --allow-fs-read='C:\Users\carlo\Documents\Playground\NODO\node_modules' --allow-fs-read='C:\Users\carlo\Documents\Playground\NODO\apps\web\node_modules' scripts/test_wallet_allowlist.cjs 'C:\Users\carlo\Documents\Playground\NODO\apps\web\node_modules\typescript'
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff check apps/api/tests/test_business_wallet_probe_static.py
& 'C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe' -B -m ruff format --check apps/api/tests/test_business_wallet_probe_static.py
~~~

Para pytest se uso el ejecutor en memoria siguiente, pasando su contenido por stdin al Python instalado con -B. SELECTION fue:
- Relacionadas: ["-p","no:cacheprovider","apps/api/tests/test_business_wallet_probe_static.py","apps/api/tests/test_business_credit_handoff_static.py","apps/api/tests/test_auth_lifecycle_static.py","-q","--tb=short","-x"].
- Completa: ["-p","no:cacheprovider","apps/api/tests","-q","--tb=short","-x"].

~~~python
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

~~~

La comprobacion de tipos uso el script siguiente por stdin a Node con los mismos permisos de lectura del comando anterior. Reutiliza dependencias ya instaladas del checkout original, sin modificar node_modules ni resolver imports relativos contra otro codigo. No emite JS ni cache incremental.

~~~javascript
const fs=require("node:fs"),path=require("node:path");
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
~~~

## Revision y limites

Revision del diff: sin cambios de contratos API, DB, estados, contabilidad, auth o roles. No hay nuevas dependencias, consultas ni polling; costo cloud adicional de esta correccion: ninguno solicitado o activado. La lista se procesa solo al construir el enlace, no en un sondeo periodico. La politica deniega por defecto y los casos adversariales cubren confusion de host, puertos, normalizacion, credenciales y privacidad. No se encontraron bloqueos nuevos en ese alcance; Dilitan debe revisar antes de avanzar.

Antes del push se verifico en UI: Cloudflare nodo-staging muestra No Git connection; Railway nodo-api-staging/nodo-api muestra Source vacio con Connect Repo/Connect Image. Los dos workflows del repositorio son workflow_dispatch, no se invocaron. No se abrieron variables ni secretos. La primera conexion Git dentro del sandbox fallo; el push autorizado fuera del sandbox publico solo esta rama, sin force.

No se ejecuto next build, navegador/Telegram/MetaMask reales, pago, firma, prueba on-chain, migracion ni deploy. Typecheck y fixtures no prueban el comportamiento de un build desplegado. No se definio un dominio productivo real. Antes de produccion faltan elegir/configurar ese dominio bajo autorizacion, integrar las ramas y validar el release real. Los pendientes previos de PostgreSQL aislado, migracion 0065 y N9 siguen vigentes.

El escaner del reporte produjo dos avisos genericos de entropia en los enlaces de Drive de TAREA-002 y su revision anterior (lineas 19-20); son identificadores de archivos ya conocidos, revisados manualmente, no credenciales. No se modifico la allowlist del escaner ni se presenta esa comprobacion documental como exit 0.

## Entrega

PR #3 permanece en borrador. Se espera APROBADO u OBSERVACIONES de Dilitan antes de TAREA-003. No se solicita al revisor implementar ni investigar por Codex. Este reporte reemplaza el estado de bloqueo documental anterior despues de la autorizacion explicita de Carlos, conservando su antecedente arriba. Se actualiza el mismo archivo Markdown en Drive y se verifica por lectura, junto con PRESENCIA-CODEX.md. No se modifica ningun archivo de Carlos o Dilitan.
