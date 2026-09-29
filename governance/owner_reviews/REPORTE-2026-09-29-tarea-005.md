# TAREA-005: disputas y ampliacion de plazo atomicas

Fecha: 2026-09-29, America/New_York.
Estado: VALIDADO_LOCALMENTE; PENDIENTE_PUBLICACION_Y_REVISION_DILITAN; SIN_MERGE_NI_DEPLOY.
Codex implementa y entrega; Dilitan revisa.
Reporte Markdown en Drive, entrega inicial verificada por lectura:
https://drive.google.com/file/d/1R3c14NEx1lqipq8i0tvEwj9zMFy090sm/view.

## Alcance y procedencia

Dilitan aprobo TAREA-004 en REVISION-2026-09-29-tarea-004-impl.md, modificada 2026-09-29T15:56:13.632Z:
https://drive.google.com/file/d/1fSa-C6iVrvxI2mEwJyGwrgV_LklPiAOr/view.
Su revision fue estatica, no una nueva ejecucion de pruebas. La decision de Carlos permanece:
sin exencion Founder; el administrador asigna creditos normales manualmente.

Se atiende solamente TAREA-005-lote-e-disputas-plazos.md:
https://drive.google.com/file/d/1Rj3mapk3gqXFItoenFyl16z4wpcKfIf8/view.
N25 y N26 se confirmaron contra codigo y contratos antes de cambiar. No se tomo TAREA-006.

## Candidato

- Base exacta: 78a5e4adf8a3ac715087c72002852251c54c002c.
- Rama base: codex/tarea-004-retirar-founder-20260929, PR #7 aprobado por Dilitan y no fusionado.
- Rama nueva: codex/tarea-005-disputas-plazos-20260929.
- Codigo, contratos y pruebas: cffe9e03849cd0aa0e84e58866fe1ce82ec1cedd.
- Enlace previsto de rama, aun pendiente de verificar publicacion: https://github.com/Goldempire-coder/NODO/tree/codex/tarea-005-disputas-plazos-20260929.
- Worktree existente reutilizado: C:/Users/carlo/Documents/Playground/NODO-credit-holds-review.
- Checkout original preservado: C:/Users/carlo/Documents/Playground/NODO, HEAD 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1.
- El futuro PR debe comparar contra la rama base anterior, NO main, para mostrar solo esta tarea.

## Cambios

1. N25: apertura generica de disputa de participantes. Orden, caso, timeline de disputa,
   timeline de orden y auditoria se escriben juntos. PostgreSQL bloquea la orden y usa
   una unica transaccion; el repositorio en memoria protege sus escritores y revierte
   solo lo agregado si falla una escritura. Notifica despues de terminar la transaccion.
2. Se revalidan titularidad, estado actual y ausencia de otra disputa abierta bajo
   el bloqueo. Se conservan validaciones previas de rol activo, motivo, evidencias,
   privacidad, rate limit e idempotencia. El flujo especial de problema de pago
   del negocio y el flujo administrativo existentes no se sustituyen.
3. N26: la ampliacion revalida propietario, estado, reporte, vencimiento y uso previo
   bajo bloqueo. Estado, timeline y auditoria se confirman juntos. Dos solicitudes
   distintas con lecturas antiguas no pueden consumir dos veces la ampliacion.
4. Se mantienen los 15 minutos, una sola ampliacion, respuestas, permisos y reglas
   actuales. No se liberan ni consumen creditos o capacidad, ni se modifican anuncios.
5. Contratos de ordenes y disputas documentan estas garantias y ORDER_STATE_CONFLICT.

## Archivos de implementacion

- apps/api/app/modules/disputes/service.py
- apps/api/app/modules/orders/memory_repository.py
- apps/api/app/modules/orders/postgres_repository.py
- apps/api/app/modules/orders/remitter_ops.py
- apps/api/app/modules/orders/memory_participant_transitions.py
- apps/api/app/modules/orders/postgres_participant_dispute.py
- apps/api/app/modules/orders/postgres_deadline_extension.py
- apps/api/tests/test_participant_order_atomicity.py
- control_plane/06_API_CONTRACTS/DISPUTES_API.md
- control_plane/06_API_CONTRACTS/ORDERS_API.md

Diez archivos, 896 inserciones y 76 eliminaciones; 474 lineas son pruebas nuevas.
Se agrega este reporte como archivo once, sin modificar los reportes versionados de tareas anteriores.

## Evidencia nueva

| Comprobacion | Resultado |
| --- | --- |
| N25 antes del arreglo | Fallo reproducido: create_dispute falla y la orden queda disputed |
| N26 antes del arreglo | Fallo reproducido: ambas solicitudes con lectura antigua devuelven exito |
| Primer recorrido de ambas regresiones tras el arreglo | 2 passed |
| Casos nuevos intermedios | 36 passed |
| Grupo final: nueva prueba, chat_disputes, order_creation, job_order_transitions, business_order_ops | 190 passed, 1 warning; 22.39 s |
| Suite completa apps/api/tests | 1482 passed, 68 skipped, 1 warning; 162.27 s |
| Casos nuevos incluidos en el grupo y suite finales | 40 |
| Intentos bloqueados de conexion/proceso externo en cada recorrido | 0 |
| Ruff: dos repositorios de integracion y cuatro archivos nuevos | Correcto |
| Formato: cuatro archivos nuevos | Correcto |
| Ruff de service/remitter_ops contra la base | Mismos 3 avisos previos, ninguno agregado |
| git diff --check y diff preparado | Correctos |
| secret-guard sobre los diez archivos completos | Salida 0, ningun hallazgo |
| Diff rastreado del checkout original | Identico al anterior; website preservado |

El primer arnes concurrente compartia un idempotency store en memoria que serializaba
ambos hilos antes de la barrera. Se corrigio exclusivamente el arnes para simular
dos workers con stores separados y repositorio compartido; asi se reprodujo N26.
Una primera ampliacion de casos comparaba el texto localizado de ApiError; se corrigio
la prueba para comprobar el codigo estable .code. No se cambio la app para ocultar
estos errores del arnes. Ningun recorrido permitio conexiones reales.

Los 40 casos cubren los cuatro estados admitidos de disputa, idempotencia,
conservacion de recursos, errores antes y despues de escrituras, ausencia de
notificaciones tras rollback, lecturas antiguas, cambios de titular/estado,
vencimiento y uso unico, dos aperturas simultaneas y dos ampliaciones simultaneas.
Los dobles PostgreSQL usan PooledConnectionContext real con conexion simulada:
comprueban FOR UPDATE, guardas SQL, unico commit final, rollback y ausencia de
escrituras ajenas. NO sustituyen un ensayo de concurrencia contra PostgreSQL real.

Las 68 omisiones no son aprobaciones. No se habilitaron pruebas opt-in con servicios.
El aviso es la deprecacion anterior Starlette/httpx; no se instalaron componentes.
Persisten I001 previo en disputes/service.py y I001/UP035 previos en remitter_ops.py.
No se afirma que el lint global este limpio ni que la base real este validada.

El escaneo separado del reporte dio salida 1 por dos avisos de entropia en los
enlaces Drive del dictamen y tarea. Se revisaron como identificadores de archivos
de coordinacion, no credenciales. No se cambiaron excepciones del escaner.

## Comandos y aislamiento

Python ya instalado: C:/Users/carlo/Documents/Playground/NODO/.venv/Scripts/python.exe.
Directorio: worktree indicado. Ejecutores temporales en memoria mediante python -B -.
No se cargaron archivos .env ni secretos. Se limpiaron las variables heredadas,
se fijaron valores ficticios de test, notificador y watcher apagados, se bloqueo
psycopg, Redis, sockets, DNS y creacion de procesos. Solo se permite el socketpair
interno que requiere el bucle local de Python. Pytest sin plugins automaticos,
bytecode ni cache, con directorio temporal nuevo y parada ante el primer fallo.

Selecciones exactas bajo ese ejecutor:
~~~text
pytest.main([
  "apps/api/tests/test_participant_order_atomicity.py",
  "apps/api/tests/test_chat_disputes.py",
  "apps/api/tests/test_order_creation.py",
  "apps/api/tests/test_job_order_transitions.py",
  "apps/api/tests/test_business_order_ops.py",
  "-q", "--tb=short", "-x", "-p", "no:cacheprovider"
], plugins=[Guard()])
pytest.main(["apps/api/tests", "-q", "--tb=short", "-x", "-p", "no:cacheprovider"],
            plugins=[Guard()])
python -B -m ruff check --no-cache <dos repositorios y cuatro archivos nuevos>
python -B -m ruff format --no-cache --check <cuatro archivos nuevos>
git show 78a5e4a:<archivo> | python -B -m ruff check --no-cache --output-format json --stdin-filename <archivo> -
python -B <secret-guard>/scripts/guard.py --files <diez archivos listados> --format json
git diff --check
git diff --cached --check
git ls-remote --heads origin main codex/integration-reviewed-fixes-20260929 codex/tarea-004-retirar-founder-20260929 codex/tarea-005-disputas-plazos-20260929
~~~

El ejecutor Guard es el mismo previamente documentado para TAREA-004; no se altera
su bloqueo ni se agrega un archivo de ejecucion a la app. Resultados de esta
seccion corresponden a ejecuciones nuevas de esta entrega, no a las de Founder.

## Aislamiento de publicacion y revision

Verificado en solo lectura antes de publicar: Cloudflare nodo-staging indica
No Git connection; Railway nodo-api-staging/nodo-api tiene Source vacio;
GitHub Webhooks no lista conexiones. Los dos workflows del candidato son
workflow_dispatch manuales, no invocados. No se cambia ninguna configuracion.

Refs remotas comprobadas: main 74e6d2658dcd545a0d4d4d9aeba8263121a75499,
integracion 2537c8e78c8fbf7ee31178a1d07deea2d5a17945, base de esta tarea
78a5e4adf8a3ac715087c72002852251c54c002c. La nueva rama aun no existia al comprobar.

Revision propia: sin hallazgos bloqueantes nuevos en el alcance; las limitaciones
anteriores se entregan a Dilitan y no se ocultan con pruebas verdes.
La apertura generica adopta el mismo patron de transacciones ya presente en otros
flujos; no se agregan dependencias ni un nuevo sistema de persistencia.

## Pendientes

- Publicar rama/PR de revision y verificar SHA remoto. Entrega inicial en Drive ya cotejada.
- Esperar dictamen de Dilitan sobre este SHA antes de tomar otra tarea.
- Concurrencia real PostgreSQL y puesta en servicio requieren entorno aislado y autorizacion separada.
- No se resuelve aqui el bloqueo previo de integracion a main, migracion 0065 o inventario Founder historico.
- No se declara NODO apto para produccion ni completado el ciclo del proyecto.

Sin merge, deploy, migraciones, instalaciones, datos reales, secretos, wallets,
bots, USDC, asignaciones reales, cambios de proveedores ni cargos nuevos.
Website y laboratorio de respaldos intactos.

## Fuentes oficiales contrastadas

- PostgreSQL 17, transacciones: https://www.postgresql.org/docs/17/tutorial-transactions.html
- PostgreSQL 17, bloqueo de filas: https://www.postgresql.org/docs/17/explicit-locking.html

Las fuentes sustentan el uso de transacciones y FOR UPDATE. No prueban por si
solas el comportamiento del despliegue de NODO.
