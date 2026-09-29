# REPORTE - TAREA-001: CORS y URLs de Telegram

Fecha local: 2026-09-28 (America/New_York).
Constructor: Codex. Revisor: Dilitan.
Estado: validacion local completa; entrega en rama de revision, sin fusion ni despliegue.

## Resumen

- Dilitan aprobo TAREA-000 mediante REVISION-2026-09-28-credit-holds.md; se continua con TAREA-001.
- Produccion ya no hereda la expresion de previews de staging; usa origenes explicitos y rechaza comodin y hosts de nodo-staging en la lista.
- Produccion exige ambas URLs de Telegram antes de crear la app; fuera de produccion se conservan sus defaults.
- Se agregaron 30 casos; 111 pruebas relacionadas y 1390 de la suite completa pasaron con conexiones bloqueadas.
- Sin tocar ordenes, creditos, datos reales, proveedores, website ni laboratorio; no es aprobacion de produccion.

## Identidad y alcance

- Repositorio existente: C:\Users\carlo\Documents\Playground\NODO. No clonado.
- Se reutilizo el worktree limpio C:\Users\carlo\Documents\Playground\NODO-credit-holds-review. Su nombre historico no cambia su alcance.
- Base exacta: 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1, codex/review-automatic-order-transitions-20260928.
- Rama: codex/cors-telegram-config-20260928.
- Commit del codigo probado: 0d8fca1c8db0afeb27d35960adb92b573cb77047.
- [Rama de revision](https://github.com/Goldempire-coder/NODO/tree/codex/cors-telegram-config-20260928).
- Se conserva PR #1 y su rama en 43016571df21eeb1217dca6fd2ffabdf5c1a3b7f. Esta segunda entrega parte de la misma base de TAREA-001, no incluye ni reemplaza el arreglo de creditos.
- No main, merge, force-push, migracion ni deploy. La integracion futura de las dos ramas requiere aprobacion; no se pierde la primera correccion.
- El checkout original tenia cambios ajenos. Status y diff se compararon antes/despues y fueron identicos, antes de actualizar exclusivamente el documento propio PRESENCIA-CODEX.

## Hallazgos confirmados

N1: _configure_middlewares pasaba una expresion de *.nodo-staging.pages.dev a CORSMiddleware en todos los ambientes. La prueba roja en la base recibio 200 cuando debia recibir 400 para un preflight de preview en produccion.

N3: load_settings suministraba defaults de staging a TELEGRAM_WEB_APP_URL y TELEGRAM_WELCOME_IMAGE_URL sin exigirlos en produccion. create_app llama load_settings antes de configurar repositorios o workers, por lo que la validacion se coloca alli.

Contraste: SOURCE_OF_TRUTH, PILOT_CONTROLLED_GATE, ENGINEERING_GUARDRAILS y SECURITY_MASTER. Ninguno autoriza comunicar con proveedores, ampliar accesos ni desplegar como parte de esta tarea.

## Cambios por archivo

| Archivo | Cambio |
|---|---|
| apps/api/app/core/config.py | Settings.cors_origin_regex; politica por ambiente; validacion de URLs requeridas y de regex invalida sin imprimir su valor |
| apps/api/app/main.py | Pasa settings.cors_origin_regex al middleware en vez de una expresion incondicional |
| .env.example | Documenta origenes exactos, regex no productiva y ambas URLs requeridas |
| apps/api/tests/test_cors_telegram_config.py | 30 casos nuevos con datos ficticios, sin modificar pruebas existentes |
| governance/owner_reviews/REPORTE-2026-09-28-cors-telegram.md | Este reporte |

## Politica efectiva

- APP_ENV=production: API_CORS_ORIGIN_REGEX no se aplica, aunque este definida con .* o con una expresion de staging. Solo API_CORS_ORIGINS puede conceder acceso CORS.
- API_CORS_ORIGINS omitida en produccion: lista vacia; no se inventa un dominio oficial. Antes de desplegar hay que definir los dominios aprobados expresamente.
- Produccion rechaza '*' y los hosts nodo-staging.pages.dev o sus subdominios incluso si se copian a la lista explicita.
- local/dev/development/staging/test: si API_CORS_ORIGIN_REGEX no existe, conserva el patron anterior. Un valor vacio desactiva el patron y uno explicito lo reemplaza. Ambientes desconocidos no heredan permisos por regex.
- El patron se compila al cargar configuracion. Una expresion invalida falla con la clave, sin imprimir la expresion ni encadenar el error con su contenido.
- Produccion: cada URL de Telegram es obligatoria y no puede estar vacia ni contener solo espacios. El error identifica las claves que faltan y ocurre antes de construir la app.
- Fuera de produccion no cambia el comportamiento previo de las URLs ni su formato.
- No cambia allow_credentials=False, los metodos HTTP, headers, autenticacion, RBAC ni controles de propiedad.

Se reutiliza EnvValidationError. Su texto heredado dice Missing required environment keys tambien para configuraciones invalidas; no se amplio el contrato de excepciones en esta tarea.

CORS controla el acceso del navegador a respuestas, no reemplaza autenticacion ni impide por si solo que una peticion directa llegue a la API. Las pruebas distinguen un preflight rechazado de una peticion simple que se procesa sin cabecera de autorizacion CORS.

## Pruebas y evidencia nueva

Entorno existente: Windows y Python 3.14 de NODO\.venv. No instalaciones, servicios locales ni conexiones externas.

| Comprobacion | Resultado |
|---|---|
| Rojo antes del cambio | 1 fallo esperado: preflight de preview productivo devolvia 200 en vez de 400; 1.76 s |
| Focal despues del cambio | 30 passed, 1 warning; 1.83 s |
| Relacionadas despues del ajuste de formato | 111 passed, 1 warning; 10.48 s |
| Suite completa | 1390 passed, 68 skipped, 1 warning; 147.13 s |
| Bloqueo de conexiones | ISOLATION_BLOCKED_COUNT 0 en todas las corridas |
| Ruff de la prueba nueva | Sin avisos; formato comprobado |
| Ruff de config.py/main.py | 5 avisos preexistentes, mismos codigos, lineas y mensajes que en 6069a75 |
| git diff --check | Sin errores |
| secret-guard de los 4 archivos de codigo/plantilla/pruebas | Sin hallazgos |
| Checkout original | Status y diff preservados |

Los cinco avisos antiguos no se ocultan ni se corrigen fuera de alcance: UP035 en config.py:6; I001 en main.py:1; BLE001 en main.py:189,233,365. El import del archivo nuevo se ordeno y su formato se corrigio antes de las relacionadas y la suite completa.

El escaneo de este reporte marca dos coincidencias genericas por los identificadores de los enlaces Drive de las fuentes. Revision manual: son enlaces a los documentos de trabajo autorizados, no credenciales ni valores secretos. No se cambio la configuracion del detector.

El warning existente es StarletteDeprecationWarning por httpx en TestClient. No se instalo otra dependencia. Las 68 omisiones no cuentan como aprobadas; esta corrida no enumero sus razones.

1390 no es la suma acumulada con PR #1: esta rama parte de 6069a75, sin las 22 pruebas de creditos de aquella rama, y agrega 30 propias.

Cobertura: preview productivo con/sin regex copiada, origen no listado, cabeceras de peticiones simples, origen oficial ficticio autorizado, lista ausente, comodin/host staging rechazados, staging/dev/test conservados, reemplazo y desactivacion del patron, regex invalida, ambiente desconocido, ambas URLs faltantes/vacias/espacios, arranque fallido antes de construir runtime y URLs explicitas conservadas.

## Comandos reproducibles y aislamiento

Directorio: C:\Users\carlo\Documents\Playground\NODO-credit-holds-review.
Ejecutable existente: C:\Users\carlo\Documents\Playground\NODO\.venv\Scripts\python.exe -B -.
El bloque siguiente se envio por stdin mediante un here-string de PowerShell; no se agrego un ejecutor al repositorio. SELECTION se sustituye por una de estas listas literales:

- Rojo/focal: ["-p","no:cacheprovider","apps/api/tests/test_cors_telegram_config.py","-q","--tb=short","-x"]
- Relacionadas: ["-p","no:cacheprovider","apps/api/tests/test_cors_telegram_config.py","apps/api/tests/test_foundation_http.py","apps/api/tests/test_admin_telegram_alerts.py","apps/api/tests/test_telegram_bot_webhook.py","apps/api/tests/test_supabase_storage_adapter.py","apps/api/tests/test_cloudflare_pages_staging_deploy_guard.py","apps/api/tests/test_auth_telegram.py","-q","--tb=short","-x"]
- Completa: ["-p","no:cacheprovider","apps/api/tests","-q","--tb=short","-x"]

El ejecutor limpia configuracion de aplicacion heredada, usa direcciones ficticias, desactiva plugins externos/workers y bloquea DB, Redis, DNS, sockets externos y procesos hijos. Solo conserva la excepcion de socketpair local interno de Python en Windows. Si se detecta un intento, la corrida falla aunque una prueba capture la excepcion. No imprime argumentos, destinos ni valores privados.

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

Comandos adicionales desde el mismo directorio:

```text
python -B -m ruff check --no-cache apps/api/tests/test_cors_telegram_config.py
python -B -m ruff format --check --no-cache apps/api/tests/test_cors_telegram_config.py
python -B -m ruff check --no-cache --output-format json apps/api/app/core/config.py
python -B -m ruff check --no-cache --output-format json apps/api/app/main.py
git show 6069a75:apps/api/app/core/config.py | python -B -m ruff check --no-cache --output-format json --stdin-filename apps/api/app/core/config.py -
git show 6069a75:apps/api/app/main.py | python -B -m ruff check --no-cache --output-format json --stdin-filename apps/api/app/main.py -
git diff --check
python -B C:\Users\carlo\.codex\skills\secret-guard\scripts\guard.py --files .env.example apps/api/app/core/config.py apps/api/app/main.py apps/api/tests/test_cors_telegram_config.py
```

En esos comandos python significa el ejecutable de la venv indicado, no una instalacion nueva. Ruff --fix --select I001 y ruff format se aplicaron solo al archivo nuevo.

## Publicacion y no despliegue

- La base remota se verifico en 6069a75; la rama nueva no existia antes de publicar.
- Cloudflare consultado nuevamente en solo lectura: nodo-staging muestra No Git connection y ultimo despliegue hace 19 dias. No se conecto a GitHub.
- Evidencia de esta misma sesion: Railway nodo-api-staging / nodo-api sin fuente Git conectada; sin modificarlo.
- Los dos workflows presentes son workflow_dispatch. No se invocaron.
- La subida usa un refspec explicito para esta rama. El SHA remoto final, los enlaces de PR y la entrega Drive se verifican antes de anunciar el cierre de la entrega.
- Sin recursos cloud nuevos, cargos de proveedores, secretos o cambios de limites. Solo validacion local y publicacion del codigo autorizado.

## Limites y siguientes pasos

- Requiere APROBADO u OBSERVACIONES de Dilitan antes de TAREA-002.
- No valida Telegram real, navegadores moviles reales, URLs oficiales, certificados, redes o configuracion desplegada. Se valido middleware ASGI y carga de configuracion en memoria con datos ficticios.
- La obligatoriedad de las URLs no verifica su propiedad ni impide que un operador configure explicitamente una URL equivocada; revisar los valores aprobados antes del despliegue sin publicarlos.
- La expresion configurable se limita a ambientes no productivos. Revisar cualquier patron personalizado antes de usarlo.
- Los dominios oficiales y los valores de produccion no se decidieron ni configuraron en esta tarea. Omitir API_CORS_ORIGINS productiva deniega acceso CORS por defecto.
- TAREA-000 conserva sus pendientes: prueba con PostgreSQL aislado y autorizacion de migracion 0065. Su aprobacion estatica no equivale a haber desplegado el arreglo.
- N9 (IP en logs) sigue pendiente de decision de Carlos y fuera de esta tarea.
- No declara NODO listo para produccion ni el respaldo real validado.

## Fuentes

- [Revision de Dilitan, TAREA-000](https://drive.google.com/file/d/1PNk1Ee5HGHg3OfTpiZSJMlCJgyQtIGRR/view).
- [TAREA-001 v2](https://drive.google.com/file/d/1uqcIwYUdi72y1E6iV6mApkGbhPOw63Ez/view).
- [FastAPI: CORS](https://fastapi.tiangolo.com/tutorial/cors/): lista explicita, regex y distincion entre preflight y peticiones simples. Contrastado con el CORSMiddleware instalado en la venv. La pagina de Starlette consultada devolvio 502; no se uso como evidencia recuperada.

