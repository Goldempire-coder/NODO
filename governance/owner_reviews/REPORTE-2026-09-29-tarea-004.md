# TAREA-004: retiro de Founder y creditos manuales normales

Fecha: 2026-09-29, America/New_York.
Estado actual: IMPLEMENTADO_Y_VALIDADO_LOCALMENTE; PENDIENTE_PUBLICACION_Y_REVISION_DILITAN.
Esta seccion sustituye la decision pendiente del diagnostico historico conservado mas abajo.

## Decision directa del Owner

Carlos indico en este chat: "yo le asigno creditos al negocio que inicie, quita esa regla de founder".
Se retira la exencion automatica; NO se implementa la propuesta anterior de confirmar gratis.
Codex implementa y entrega; Dilitan revisa. No hay autorizacion nueva de main, migracion o deploy.

## Candidato

- Base exacta: 2537c8e78c8fbf7ee31178a1d07deea2d5a17945, rama codex/integration-reviewed-fixes-20260929.
- Rama de esta tarea: codex/tarea-004-retirar-founder-20260929.
- SHA de codigo, contratos y pruebas: 0a84eaa0b47ec56ab521f76ab0dd6e1d4d287016.
- Enlace de rama destinado a revision (publicacion aun pendiente en esta version): https://github.com/Goldempire-coder/NODO/tree/codex/tarea-004-retirar-founder-20260929.
- Worktree limpio reutilizado: C:/Users/carlo/Documents/Playground/NODO-credit-holds-review.
- No se incorporo el script del ensayo PR #6. No se cambio el checkout original, main ni otras ramas.
- Reporte Drive existente que se actualiza: https://drive.google.com/file/d/1YylenZzmjAj5tA2VhWy6x6PNTGtOcjQq/view.

## Cambio realizado

1. Eliminadas la comprobacion del beneficio y la opcion interna use_founder_access en publicacion. Memoria y PostgreSQL siempre exigen saldo, reservan creditos y adjuntan el ledger hold dentro del flujo normal.
2. El ajuste administrativo existente permite asignar creditos normales con permisos, motivo, auditoria e idempotencia. No se agregan rutas ni permisos ni se ejecutan asignaciones reales.
3. Se mantiene el consumo normal al confirmar. No se fabrica hold ni consumo para movimientos founder_free_use historicos, ni se usan reservas de otros anuncios.
4. Un anuncio previo sin credit_hold_ledger_id no puede abrir una orden nueva: AD_NOT_AVAILABLE (409). El servicio lo comprueba antes de persistir y PostgreSQL lo revalida en el UPDATE atomico; no crea orden ni reserva capacidad.
5. Retirada la etapa automatica de expiracion Founder y sus nuevos avisos. Se conserva la expiracion normal de anuncios/ordenes y sus protecciones.
6. Campos Founder, tipos de ledger, errores y registros historicos conservados para compatibilidad. Los nombres internos heredados de algunos modulos y metodos sin llamadas no otorgan beneficios.
7. Contratos activos alineados con la decision: sin mes gratuito, publicacion con hold obligatorio, creditos iniciales por ajuste manual. Los catalogos historicos no se borran.

## Evidencia nueva

| Comprobacion | Resultado |
| --- | --- |
| Regresion antes del arreglo, aislada | 1 fallo esperado: Founder activo y saldo cero publicaba 201 en lugar de 409; cero conexiones |
| Primer recorrido nuevo | 6 passed |
| Relacionadas: ads, credits, business order ops, jobs, controles PostgreSQL y casos nuevos iniciales | 225 passed, 9 skipped, 1 warning; 50.97 s |
| Casos nuevos finales, incluidos dobles PostgreSQL | 9 passed, 1 warning |
| Suite completa apps/api/tests | 1442 passed, 68 skipped, 1 warning; 163.91 s |
| Intentos de conexion/proceso externo bloqueados durante cada ejecucion | 0 |
| Ruff en prueba nueva y formato | Correctos; se ordenaron imports y formateo solo la prueba nueva |
| Ruff en todos los Python tocados, contra blobs de base | 50 avisos actuales, mismos 50 codigos/mensajes por archivo en la base; ninguno nuevo |
| git diff --check | Correcto; se quito una linea vacia final sobrante |
| secret-guard del diff preparado, 39 archivos | Salida 0, sin hallazgos |

El aviso unico es la deprecacion previa de httpx en Starlette TestClient. Las 68 omisiones no son pruebas aprobadas; no se habilitaron suites opt-in que requieren PostgreSQL u otros entornos. No se afirma que el lint global este limpio. No hubo instalaciones.

Escaneo separado del reporte: salida 1 por 24 avisos genericos de entropia. Se cotejaron como enlaces GitHub/Drive ya verificados y rutas de contratos en la lista de archivos y diagnostico historico; no son credenciales. No se cambio ninguna allowlist ni se presenta esa salida como verde automatico. El diff de implementacion dio salida 0.

Los nueve casos nuevos cubren cuatro estados historicos Founder sin saldo, asignacion manual de administrador y consumo idempotente, anuncio historico sin hold, publicacion PostgreSQL sin/con saldo mediante dobles y rechazo transaccional al faltar hold. Se preservan controles anteriores de acceso, riesgo, privacidad, auditoria, locks y saldo.

## Comandos y aislamiento

Desde el worktree citado, usando solo Python instalado en C:/Users/carlo/Documents/Playground/NODO/.venv/Scripts/python.exe:

- Ejecutado por stdin con -B - el ejecutor temporal en memoria documentado en governance/owner_reviews/REPORTE-2026-09-29-integracion-cuatro-paquetes.md, seccion "Python: ejecutor temporal en memoria".
- Entorno heredado limpiado; APP_ENV=test; emisores desactivados; direcciones ficticias 127.0.0.1:1; pytest sin plugins automaticos ni cache.
- Guardias para PostgreSQL, Redis, DNS, sockets y procesos externos. Solo se permite el socketpair interno de la biblioteca estandar, no servicios. Registra prueba/categoria, no argumentos, destinos o secretos; cualquier intento conserva el fallo y detiene la suite.
- Seleccion focal: apps/api/tests/test_founder_retirement.py.
- Relacionadas: test_founder_retirement.py, test_ads_marketplace.py, test_credits_referrals.py, test_business_order_ops.py, test_jobs_notifications.py, test_operational_publication_holds_postgres.py y test_rating_pause_enforcement_postgres.py, todas en apps/api/tests.
- Suite completa: pytest.main(["apps/api/tests", "-q", "--tb=short", "-x", "-p", "no:cacheprovider"], plugins=[Guard()]).
- Ruff: python -B -m ruff check --no-cache --output-format json, sobre los 15 Python tocados. Para la base: git show 2537c8e:ruta enviado a ruff check --stdin-filename ruta -; se cotejaron los 50 avisos por archivo/codigo/mensaje, sin ocultar errores.
- Formato: python -B -m ruff format --check --no-cache apps/api/tests/test_founder_retirement.py.
- Revision: git diff --check, git diff --cached, git status, git ls-remote y secret-guard/scripts/guard.py --format json sobre el diff preparado, sin modificar allowlists.

## Archivos incluidos

- apps/api/app/modules/ads/audit_events.py
- apps/api/app/modules/ads/management.py
- apps/api/app/modules/ads/memory_repository.py
- apps/api/app/modules/ads/postgres_publish.py
- apps/api/app/modules/ads/service.py
- apps/api/app/modules/jobs/ad_founder_expiration_processor.py
- apps/api/app/modules/jobs/worker.py
- apps/api/app/modules/orders/create_order_flow.py
- apps/api/app/modules/orders/postgres_create_order.py
- apps/api/tests/test_ads_marketplace.py
- apps/api/tests/test_credits_referrals.py
- apps/api/tests/test_jobs_notifications.py
- apps/api/tests/test_operational_publication_holds_postgres.py
- apps/api/tests/test_rating_pause_enforcement_postgres.py
- control_plane/00_GOVERNANCE/DECISION_LOG.md
- control_plane/01_PRODUCT/SPEC_MASTER.md
- control_plane/03_DOMAIN_RULES/CREDITS_AND_BILLING_MASTER.md
- control_plane/03_DOMAIN_RULES/FOUNDER_RULES.md
- control_plane/03_DOMAIN_RULES/NOTIFICATION_RULES.md
- control_plane/04_DATA/DATABASE_CONSTRAINTS.md
- control_plane/05_SECURITY/RBAC_PERMISSION_MATRIX.md
- control_plane/06_API_CONTRACTS/ADS_API.md
- control_plane/06_API_CONTRACTS/API_OVERVIEW.md
- control_plane/06_API_CONTRACTS/CREDITS_API.md
- control_plane/06_API_CONTRACTS/ORDERS_API.md
- control_plane/08_SCREENS/business/B-04_BUSINESS_DASHBOARD.md
- control_plane/08_SCREENS/business/B-08_CREATE_AD.md
- control_plane/09_SLICES/SLICE_CONTRACTS_MASTER.md
- control_plane/09_SLICES/slice_03_ads_marketplace/DATA_CONTRACT.md
- control_plane/09_SLICES/slice_03_ads_marketplace/STATE_CONTRACT.md
- control_plane/09_SLICES/slice_08_credits_referrals/QA.md
- control_plane/09_SLICES/slice_08_credits_referrals/SCOPE.md
- control_plane/09_SLICES/slice_08_credits_referrals/STATE_CONTRACT.md
- control_plane/09_SLICES/slice_10_jobs_notifications/API_CONTRACT.md
- control_plane/09_SLICES/slice_10_jobs_notifications/README.md
- control_plane/09_SLICES/slice_10_jobs_notifications/SCOPE.md
- control_plane/09_SLICES/slice_10_jobs_notifications/STATE_CONTRACT.md
- control_plane/10_QA/SECURITY_TESTS.md
- apps/api/tests/test_founder_retirement.py

El commit de implementacion incluye 9 archivos de aplicacion, 6 de pruebas y 24 de contratos/documentacion: 39 archivos, +346/-173. La mayoria de ajustes documentales son una o dos lineas para retirar afirmaciones contradictorias. Este reporte se agrega aparte; PRESENCIA-CODEX.md se entrega solo en la carpeta de coordinacion.

## Revision y publicacion segura

Revision propia: sin hallazgos bloqueantes adicionales en el cambio acotado; aceptable para revision con los limites de despliegue indicados abajo. El paso gratis y su auditoria dejan de producirse; ambos repositorios usan el mismo camino normal. No hay cambios de permisos ni de tasas, importes de creditos o consumo por anuncio. El filtro PostgreSQL no agrega consultas. Se elimina la consulta periodica de expiracion Founder.

Antes de subir, comprobado por lectura actual:
- Cloudflare nodo-staging: No Git connection.
- Railway nodo-api-staging/nodo-api: Source vacio, opciones Connect Repo/Connect Image.
- Workflows del candidato solo workflow_dispatch; no se dispararon.
- Sin core.hooksPath y solo hooks .sample.
- ls-remote confirma la base 2537c8e y main 74e6d2658dcd545a0d4d4d9aeba8263121a75499; la rama nueva todavia no existia.

## Pendientes y limites

- Falta revision de Dilitan del candidato exacto. No tomar TAREA-005 mientras 004 siga en revision.
- Antes de desplegar hace falta inventario autorizado de anuncios/ordenes historicos sin hold y avisos Founder ya pendientes. No se consulto DB real; no se afirma que existan ni que no existan.
- Las ordenes ya creadas sin hold conservan la proteccion y pueden seguir rechazando confirmacion. Este cambio no las repara retroactivamente. Tampoco oculta anuncios historicos en el listado: impide nuevas ordenes sobre ellos. Su gestion se decide tras el inventario, sin usar saldos ajenos.
- No se valida aqui concurrencia real de PostgreSQL ni migracion/rollback 0065. Se conserva la parada de PR #5 hacia main por diferencia de linaje. No hubo merge.
- Sin cambios frontend/website/laboratorio, instalaciones, secretos, wallets, bots, USDC, servicios ni configuracion cloud. El diff rastreado del checkout original permanece identico al previo.
- No se asignaron creditos a negocios reales, no hubo pruebas reales de navegador/Telegram ni deploy. No se declaran resuelto el historial, validado el respaldo o NODO listo para produccion.

## Diagnostico historico previo (sustituido por la decision anterior)

Todo lo que sigue describe la lectura anterior a la respuesta del Owner. La pregunta y propuesta de gratuidad ya NO estan pendientes ni son la solucion elegida.

### Diagnostico anterior: Founder y decision entonces pendiente

Fecha: 2026-09-29, America/New_York.
Estado: REQUIERE_A_CARLOS; BLOCKED_BY_CONTRACT_CONFLICT.
Alcance realizado: lectura de codigo y contratos, sin modificaciones de producto ni pruebas.

## Recepcion y prioridad

Se leyeron [TAREA-004](https://drive.google.com/file/d/1SLpY3voVVMwn60Ryl6i9rs99hja8D34s/view) y los cinco lotes posteriores. Solo se diagnostica la TAREA-004 prioritaria; los demas quedan en cola, no se implementan simultaneamente.

Tambien se recibieron [la revision del bloqueo PR #5](https://drive.google.com/file/d/1Fw-bMzrJlr1caGyaHhErQYb37LWInYoH/view), BLOQUEADO, y [DECISION-2026-09-29-opcion-a-linaje.md](https://drive.google.com/file/d/14DR_eZyMrAlGsARACAU7n6MTHwp52r3r/view). Este ultimo documento comunica via Dilitan la opcion de auditar el linaje antes de main. Se mantiene la parada de main ya establecida. No se usa ese archivo para ampliar el permiso automatico hacia refactorizaciones generales, servicios reales o una alteracion del orden de las operaciones sobre DB. La confirmacion directa anterior de Carlos para PR #5/0065 no se borra; ninguna de las dos operaciones se ha ejecutado.

## Identidad del codigo inspeccionado

- Repositorio original conservado: C:/Users/carlo/Documents/Playground/NODO, rama codex/review-automatic-order-transitions-20260928; ultimo SHA comprobado 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1.
- Checkout de lectura: C:/Users/carlo/Documents/Playground/NODO-credit-holds-review, limpio, rama codex/credit-holds-postgres-drill-20260929, SHA bda6d6b69d792d118d706635ac9ce9489f9a4c4f.
- [Codigo inspeccionado](https://github.com/Goldempire-coder/NODO/tree/bda6d6b69d792d118d706635ac9ce9489f9a4c4f).
- `git diff --name-only 2537c8e78c8fbf7ee31178a1d07deea2d5a17945 bda6d6b69d792d118d706635ac9ce9489f9a4c4f -- apps/api/app control_plane`: salida 0, sin diferencias. La logica y contratos inspeccionados coinciden con el candidato integrado.
- No se creo ni cambio una rama para esta tarea; no existe PR de correccion TAREA-004. La futura implementacion debera partir de una base comprobada y usar su rama aislada.

## Lo demostrado por lectura

1. `apps/api/app/modules/ads/postgres_publish.py:48` no modifica saldos cuando `use_founder_access` es verdadero. La linea 61 omite adjuntar hold y la linea 136 registra `founder_free_use`, no `hold`. Su importe es informativo; no representa creditos reservados.
2. `apps/api/app/modules/orders/postgres_payment_confirmation.py:79` rechaza el anuncio sin `credit_hold_ledger_id` con `CREDIT_HOLD_NOT_FOUND` (409), sin alternativa Founder. La ruta de confirmacion llama este metodo desde `business_payment_confirmation_ops.py:88`.
3. Quitar solo esa comprobacion o adjuntar el ledger Founder como si fuera un hold no es suficiente ni seguro. `postgres_payment_credit_consumption.py:26` sigue exigiendo saldo bloqueado; la linea 63 descuenta ese saldo y aumenta el consumido. Con saldo de otro anuncio se podria consumir una reserva ajena; con saldo cero seguiria fallando. Es una consecuencia del algoritmo, no un incidente observado en datos reales.
4. El camino en memoria tambien consume obligatoriamente: `business_payment_confirmation_ops.py:103` llama `consume_hold_for_order`, y `apps/api/app/modules/ads/memory_credits.py:129` rechaza la ausencia del hold.
5. `apps/api/app/modules/orders/business_payment_confirmation_builder.py` requiere un ledger de consumo, informa `credits.consumed = ledger.amount` y emite `credits_consumed`. Una excepcion Founder debe reflejar correctamente que no hubo consumo; no fabricar un movimiento o un saldo para satisfacer el formato.
6. `apps/api/app/modules/jobs/order_expiration_processor.py:151` abre disputa para una orden que siga `payment_reported` al vencer su plazo de respuesta. El atasco descrito puede llegar a esa ruta si se cumplen esas condiciones y el job corre. NO se demuestra que toda orden Founder termine siempre en disputa, que haya pagos reales ni que exista un incidente en staging: no se consultaron datos ni servicios.

## Contradiccion de contratos

- `control_plane/03_DOMAIN_RULES/FOUNDER_RULES.md:19` permite publicar sin debitar creditos; linea 24 exige `founder_free_use`, con importe de los creditos que se habrian bloqueado. Su seccion de expiracion habla de nuevas publicaciones.
- `control_plane/03_DOMAIN_RULES/CREDITS_AND_BILLING_MASTER.md:198` prescribe publicacion gratuita con auditoria; linea 345 crea hold cuando NO aplica Founder.
- `control_plane/06_API_CONTRACTS/BUSINESS_ORDERS_API.md:245` y siguientes exigen consumo, wallet, ledger consume y auditoria; linea 288 ordena rechazar si falta hold valido. No definen la excepcion Founder de esta confirmacion.
- `control_plane/09_SLICES/slice_06_business_order_ops/DATA_CONTRACT.md:53` exige ledger consume y linea 74 exige hold valido; `slice_08_credits_referrals/STATE_CONTRACT.md:48` dice que Founder no acredita la wallet y publica sin cobrar.
- La busqueda focal en DECISION_LOG no encontro una regla explicita que reconcilie esta confirmacion sin hold y la permanencia de la exencion despues de vencer Founder. Esto no sustituye una auditoria semantica completa del linaje.

La premisa propuesta en la tarea, "todo anuncio publicado tiene hold adjunto", no se puede adoptar para Founder sin contradecir el contrato de gratuidad. La correccion puede ser acotada, pero debe explicitar esa excepcion antes de implementarla. No se debe bloquear una funcionalidad Founder permitida ni cobrarle para ocultar el bug.

## Pregunta enviada a Carlos

Se solicito confirmar: un anuncio publicado gratis durante el beneficio puede completar sus ordenes sin cobrar ni reservar creditos, aunque el beneficio venza despues, siempre que exista el registro verificable de esa publicacion gratuita y se mantengan todos los demas controles.

Pendiente de respuesta. No se registro una respuesta supuesta ni se editaron contratos como si estuvieran aprobados.

## Propuesta minima, pendiente de la decision

- Mantener la publicacion Founder gratuita y su registro verificable ligado al mismo anuncio y negocio; no identificar la exencion solo por ausencia de hold ni por el estado Founder actual.
- Reconciliar expresamente contratos de confirmacion y auditoria. Para la exencion legitima, confirmar orden/reporte y archivar anuncio sin alterar los saldos ni fabricar hold/consume. Definir una respuesta que represente correctamente cero consumo y la evidencia de exencion.
- Preservar exigencia de hold, consumo real e idempotencia para publicaciones normales. Sin evidencia Founder valida, continuar rechazando la ausencia del hold.
- Preservar ownership, negocio aprobado, estados, reporte submitted, limites, disputas por causas reales e idempotencia. Resolver la confirmacion transaccionalmente; no desactivar el job de disputas.
- Validar ambos repositorios y el recorrido publicar/crear/reportar/confirmar con datos ficticios; agregar regresion normal, anuncio sin hold ni exencion, evidencia de otro negocio/anuncio, reintentos y saldo bloqueado de otros anuncios intacto. Segun la decision, cubrir expiracion posterior del beneficio. Estos casos estan propuestos, no ejecutados.

## Cola nueva, sin ejecucion

| Tarea | Lectura de alcance, no veredicto de sus bugs |
| --- | --- |
| [005 disputas/plazos](https://drive.google.com/file/d/1Rj3mapk3gqXFItoenFyl16z4wpcKfIf8/view) | Atomicidad y carreras; contrastar despues de cerrar/revisar 004. |
| [006 mantenibilidad](https://drive.google.com/file/d/1AIu9Z79UCZgWCSZQEFWKsRU_F7wV-ii2/view) | Contiene refactorizaciones amplias, incluidas superficies wallet; no autorizadas automaticamente por llamarlas hallazgos. |
| [007 rate limits](https://drive.google.com/file/d/1PSj0QUrxfkBB3P8q-7MZKLUMdPAD5rB3/view) | Validar las premisas y configuracion de proxies antes de cambios; no incorporar registro nuevo de IP. |
| [008 flujos](https://drive.google.com/file/d/1sbbRzaXuqcgh7kqGwEayCg4g-IaCy2XN/view) | Mezcla bugs con cambio de arquitectura de sesiones/cookies; separar y pedir decision antes de ese cambio amplio. |
| [009 endurecimiento](https://drive.google.com/file/d/1WfFuQwLDoBl5-WLXZ3OCnDN-y5fn9EZ7/view) | Incluye retiros de rutas y cambios de ventana de autenticacion; comprobar compatibilidad/contrato y alcance antes de tocar. |

## Comandos, resultados y limites

Se usaron `git status --short --branch`, `git rev-parse --show-toplevel HEAD`, el diff focal indicado, `rg -n`/`rg -n -C` para nombres Founder/hold/callers y `Get-Content` para codigo, contratos y gobernanza. Se leyeron documentos nuevos via conector Drive, sin modificarlos.

Resultado: bloqueo de confirmacion identificado estaticamente; requiere reconciliacion de contrato. No se ejecuto ningun test, servicio, consulta DB, backup, migracion, instalacion, build, commit, push, merge o deploy. No se leyeron secretos ni datos reales, ni se modificaron wallets, bots, USDC o configuraciones cloud.

Archivos propios afectados: este reporte y PRESENCIA-CODEX.md en governance/owner_reviews del repositorio original. Sin cambios en la app, pruebas o control_plane. Se preservan todos los cambios existentes de website y laboratorio. Entrega Markdown en Drive con comprobacion por lectura. No se declara resuelto el bug, terminada la auditoria ni listo el proyecto para produccion.
