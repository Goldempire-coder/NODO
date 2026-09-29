# TAREA-007: limites de solicitudes y concurrencia local

Fecha: 2026-09-29, America/New_York.
Estado: ENTREGADO_PARA_REVISION_DILITAN; VALIDADO_LOCALMENTE; SIN_MERGE_NI_DEPLOY.
Codex comprueba, implementa y entrega; Dilitan revisa. Esta entrega no aprueba produccion.

## Decision de Carlos y continuidad

Carlos indico: "Dale pero actualiza el reporte a dilitan para que todo quede documentado en los dos lados".
Se registra su decision: TAREA-006 queda pospuesta completa, incluido N14, como deuda visible.
Su reporte y PRESENCIA-CODEX.md fueron actualizados localmente y en Drive y comprobados por lectura.
No se implementa ninguna parte de TAREA-006 ni se inicia TAREA-008.
TAREA-005 ya fue aprobada por Dilitan sobre su candidato; no se fusiona aqui.

Tarea atendida: TAREA-007-lote-g-rate-limit.md (N10, N11, N12 y N20).
https://drive.google.com/file/d/1PSj0QUrxfkBB3P8q-7MZKLUMdPAD5rB3/view.
No se cambia codigo solo por la propuesta: se reprodujeron los cuatro fallos localmente antes del arreglo.
Se conserva la decision de Carlos de NO agregar registro/seguimiento de direcciones IP.

## Candidato

- Base exacta: b16884bbbcf1ab546a106d7ce49812ed0a03a85d.
- Base de revision: codex/tarea-005-disputas-plazos-20260929 (PR #8), no main.
- Rama: codex/tarea-007-rate-limit-20260929.
- Commit de codigo, pruebas, plantillas y contrato: b56111e3e103c8fdaee3a5f1044dec7ef2fc2568.
- Rama publicada, comprobada por ls-remote:
  https://github.com/Goldempire-coder/NODO/tree/codex/tarea-007-rate-limit-20260929.
- Worktree existente: C:/Users/carlo/Documents/Playground/NODO-credit-holds-review.
- Checkout original preservado: C:/Users/carlo/Documents/Playground/NODO,
  HEAD 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1.
- Main remoto comprobado por ls-remote: 74e6d2658dcd545a0d4d4d9aeba8263121a75499; no modificado.
- PR #9 creado en borrador contra TAREA-005, sin fusionar ni marcar listo:
  https://github.com/Goldempire-coder/NODO/pull/9.
- Reporte Markdown en Drive, mismo contenido que la copia local:
  https://drive.google.com/file/d/1AqgoMRPkpFogFXT6zttWZRkEhb6DUWQO/view.
- El commit posterior al SHA funcional agrega unicamente este reporte; no cambia el
  candidato probado. Su SHA de entrega se registra en PRESENCIA-CODEX.md y en el PR.
- Entrega para revision, no cierre de tarea: esperar el dictamen de Dilitan antes
  de avanzar. Las comprobaciones omitidas y los pendientes operativos siguen abiertos.

## Hallazgos comprobados y correccion

1. N10: con el codigo anterior, un peer no confiable podia cambiar la identidad rotando XFF.
   Ahora el default ignora XFF. Solo se aceptan cabeceras desde proxies IP/CIDR configurados
   explicitamente. Se recorre la cadena de derecha a izquierda hasta el primer salto no
   confiable; un salto malformado no se salta. Se combinan cabeceras multiples en orden.
   Configuracion invalida se rechaza sin imprimir su valor; no comodines, DNS ni /0.
2. N11: 1.000 llaves caducadas seguian retenidas tras una nueva solicitud. Ahora hay limpieza
   diferida cada 60 segundos, en una solicitud, conservando contadores activos y ventanas.
   No hay hilo/servicio adicional. Si no llegan solicitudes no crece el almacenamiento y la
   limpieza espera a la siguiente. La cardinalidad activa sigue siendo un limite conocido.
3. N12: una computacion bloqueaba otra llave independiente. Ahora el bloqueo global solo
   protege mapas; cada llave tiene un bloqueo propio, compartido tambien por put().
   Se cuentan titulares y esperadores para no reemplazar un bloqueo todavia usado.
   Tras salir el ultimo se elimina. Misma llave: un computo, replay o conflicto de payload;
   distinta llave: puede progresar sin esperar I/O ajeno. TTL, errores y profiling se conservan.
   Se descarto la sugerencia de computar fuera de todo bloqueo y verificar despues:
   eso permitiria duplicar efectos antes de detectar la carrera.
4. N20: dos clientes ficticios tras un proxy explicito quedaban en el mismo limite auth.
   Las cuatro rutas auth pasan el hash transitorio del mismo middleware que usan creditos.
   El peer original usado previamente por sesiones se pasa por separado; no se guarda el
   cliente resuelto de XFF en sesiones, auditoria, logs ni respuestas.
5. Dockerfile incorpora --no-proxy-headers para que Uvicorn no sustituya el peer antes
   de que la aplicacion decida la confianza. No se construyo ni desplego una imagen.
   Este cambio exige comprobaciones HTTPS/proxy antes de cualquier despliegue (ver pendientes).

El riesgo concreto N12 probado es serializacion global. RLock ya era reentrante en el mismo
hilo: no se presenta la hipotesis general de deadlock del reporte como un incidente demostrado.

## Archivos

- .env.example
- .env.staging.example
- Dockerfile
- apps/api/app/core/config.py
- apps/api/app/main.py
- apps/api/app/modules/users/service.py
- apps/api/app/routes/auth.py
- apps/api/app/shared/idempotency/store.py
- apps/api/app/shared/rate_limit/in_memory.py
- apps/api/app/shared/rate_limit/request_identity.py
- apps/api/tests/test_hardening_local.py
- apps/api/tests/test_rate_limit_boundaries.py
- control_plane/06_API_CONTRACTS/AUTH_API.md
- governance/owner_reviews/REPORTE-2026-09-29-tarea-007.md (este reporte).

Commit funcional: 13 archivos, 608 inserciones y 28 eliminaciones; 435 lineas son pruebas nuevas.
No se cambio la implementacion de Redis, el servicio de creditos, reglas monetarias ni bases de datos.

## Evidencia nueva

- Reproduccion previa al arreglo: 4 failed, 1 warning, 2.81 s; los cuatro fallos esperados.
- Primera validacion ampliada: 37 passed y un fallo del caso nuevo por comparar el texto
  traducido de ApiError con su codigo. Se corrigio la prueba para inspeccionar .code,
  sin cambiar errores de la app ni omitir verificaciones.
- Validacion focal intermedia: 41 passed, 1 warning, 2.32 s.
- Candidato final agrega prueba de contencion sostenida y 2 casos auth/creditos:
  43 casos nuevos incluidos en las corridas relacionada y completa.
- Relacionadas: 253 passed, 1 warning, 39.47 s.
- Suite completa posterior al ultimo ajuste de formato: 1525 passed, 68 skipped,
  1 warning, 159.93 s. No se alteraron marcas de skip ni se instalaron dependencias.
- En todas las corridas: ISOLATION_BLOCKED_COUNT 0.
- Aviso existente: deprecacion de httpx en Starlette TestClient. No se instalo httpx2.
- Pruebas de proxy con IPv4/IPv6, puertos, cabeceras multiples, cadenas invalidas, peer
  ausente, default seguro, config explicita y rechazo de redes universales.
- Pruebas de privacidad: identidad resuelta no aparece en sesiones/auditoria; se conserva
  el hash del peer previo. El contexto vuelve a unknown fuera de la solicitud.
- Ocho solicitudes concurrentes de la misma llave esperan un unico compute; llaves
  distintas avanzan con el primero retenido. Se comprueban conflicto, error/reintento,
  TTL, profiling, reentrada en otra llave y liberacion de locks.
- Creditos: prueba del limitador solamente, sin crear compras ni operar wallets/USDC.
- Ruff E,F,I y formato sin errores en prueba nueva y dos modulos de rate limit.
  Comparacion con HEAD base de los otros seis archivos Python: 155 avisos previos,
  153 actuales, sin nuevas firmas de aviso. No se hizo limpieza general ajena.
- git diff --check y diff --cached --check: sin errores.
- Secret-guard sobre los 13 archivos completos: 4 avisos revisados, todos preexistentes:
  3 nombres de buckets de ejemplo y el placeholder whsec_local_hardening_placeholder
  de una prueba. No son credenciales reales; diff de esos valores sin cambios.
  No se ignoro el resultado ni se creo una allowlist.
- Escaner del reporte: 2 avisos de entropia, comprobados como los enlaces Drive
  de la tarea y de esta entrega; no contienen credenciales. Sin allowlist.

## Comandos y aislamiento

Python existente: C:/Users/carlo/Documents/Playground/NODO/.venv/Scripts/python.exe.
No se usa un pytest desnudo con el entorno del usuario. Se invoco python -B - mediante
ejecutor temporal en memoria que limpia el entorno heredado, usa APP_ENV=test,
credenciales ficticias y destinos DB/Redis 127.0.0.1:1, desactiva workers,
plugins automaticos y cache/bytecode. Bloquea PostgreSQL, Redis, conexiones/DNS/socket
externos, subprocess y os.system; identifica solo prueba/categoria si algo se bloquea.
Unicamente admite el socketpair interno de Python requerido por TestClient.
No se inicio servidor HTTP, DB, Redis, bot ni contenedor.

Argumentos pytest de la corrida relacionada:
```text
apps/api/tests/test_rate_limit_boundaries.py
apps/api/tests/test_auth_telegram.py
apps/api/tests/test_auth_admin_credentials.py
apps/api/tests/test_redis_rate_limiter.py
apps/api/tests/test_hardening_local.py
apps/api/tests/test_cors_telegram_config.py
apps/api/tests/test_credits_referrals.py
apps/api/tests/test_credit_hold_idempotency.py
-q -x -p no:cacheprovider
```

Argumentos de la suite completa: apps/api/tests -q -x -p no:cacheprovider.
Otras verificaciones: python -B -m ruff check --no-cache --select E,F,I;
ruff format --no-cache sobre los tres archivos pequenos; secret-guard --files
(lista explicita anterior, sin este reporte) --format json; git diff --check.
Comparacion Ruff base: git show b16884b:<archivo> por stdin a Ruff frente al archivo actual.
Todas las operaciones Git usan safe.directory por invocacion, sin cambiar configuracion global.

## Revision de seguridad, costo y alcance

Sin cambios de API publica, permisos, estados, contabilidad, migraciones, almacenamiento
privado, UI, website, bots, secretos, wallets o laboratorio de respaldos.
La identidad de limite es un hash seudonimo transitorio, no una promesa de anonimato.
No se agregan requests, consultas DB ni llamadas Redis por solicitud respecto al flujo previo.
Costo proveedor adicional de este trabajo: no se construyo, ejecuto ni contrato ningun servicio.
La limpieza es O(K) una vez por intervalo sobre llaves locales; no en cada solicitud.
Los locks por llave son locales al proceso. No constituyen prueba de concurrencia real
PostgreSQL/Redis ni sustituyen los controles persistentes existentes.
No se midio capacidad productiva, p95 ni carga real. No se declara escalabilidad ilimitada.
Revision local: aceptable para revision de Dilitan con los pendientes operativos siguientes.

## Aislamiento para publicacion de rama

Comprobacion nueva, solo lectura, antes del push:
- Cloudflare nodo-staging: No Git connection.
- Railway nodo-api-staging, servicio nodo-api: Source vacio / Connect Repo / Connect Image.
- GitHub settings/hooks: sin webhooks listados.
- Los dos workflows del repo solo declaran workflow_dispatch.
- Rama remota base sigue en b16884b; rama nueva aun inexistente al preflight.
No se invoco Agent, workflow, deploy, reinicio, configuracion o limites cloud.
El nombre production del entorno Railway no se toma como autorizacion productiva.

## Pendientes que NO quedan resueltos con tests locales

1. Dilitan debe revisar el SHA funcional y el diff contra TAREA-005. No se avanza a TAREA-008.
2. Antes de integrar/desplegar: verificar proxies reales, XFF append/sanitize, aislamiento
   del origen y command override. No inventar CIDRs Railway ni confiar en todo RFC1918.
   Con TRUSTED_PROXIES vacio, el default seguro puede seguir agrupando usuarios tras un proxy.
3. --no-proxy-headers tambien deja de aplicar X-Forwarded-Proto. Comprobar HTTPS y
   redirecciones de slash en staging autorizado; no declarar compatibilidad productiva
   solo por los tests ASGI o por el test estatico de Dockerfile.
4. Imagen real y comandos alternativos no ejecutados; dependencias existentes usan rangos,
   no se fijaron ni actualizaron versiones en esta tarea.
5. 68 pruebas omitidas permanecen pendientes segun sus requisitos; no se autorizan servicios
   reales para ponerlas verdes. Las pruebas locales no validan recuperacion ni produccion.
6. TAREA-006 sigue pospuesta. Las integraciones previas/main/migracion 0065 no se ejecutan aqui.

## Fuentes contrastadas

- Mozilla MDN, X-Forwarded-For:
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For.
- Documentacion oficial Uvicorn, seccion HTTP:
  https://github.com/Kludex/uvicorn/blob/main/docs/settings.md.
  Se consulto su raw oficial porque www.uvicorn.org/settings devolvio timeout.
- Python threading/RLock:
  https://docs.python.org/3/library/threading.html#rlock-objects.
- Codigo instalado de Uvicorn proxy_headers.py, solo lectura: confirma que puede mutar
  scope.client antes de la aplicacion. Esto no identifica la topologia real del proveedor.
