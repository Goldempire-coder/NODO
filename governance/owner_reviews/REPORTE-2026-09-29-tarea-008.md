# TAREA-008: adjuntos y anuncios, entrega para revision

Fecha: 2026-09-29. Estado: ENTREGADO_PARA_REVISION_DILITAN; sin merge ni deploy.
Carlos autorizo: "Corregir primero los tres bugs; sesion pendiente".
N19 queda PENDIENTE_DOCUMENTADO, no implementado ni resuelto. No se cambia autenticacion.
TAREA-006 permanece pospuesta completa, incluido N14. No iniciar 009 antes del dictamen de Dilitan.

## Alcance y trazabilidad

Fuente: TAREA-008-lote-h-flujos.md; TAREA-007 aprobada por Dilitan.
Base exacta: eeec3539e1578a3dec070619dae7a9ac415449f4.
Rama: codex/tarea-008-flujos-20260929.
Enlace: https://github.com/Goldempire-coder/NODO/tree/codex/tarea-008-flujos-20260929
Commit funcional: c9efdb161b33769b3b9f801e06b8e9b83542cb1a.
PR de revision en borrador: https://github.com/Goldempire-coder/NODO/pull/10
Base del PR: codex/tarea-007-rate-limit-20260929, no main.
Reporte Drive: https://drive.google.com/file/d/10qm1-LQA6Nj0Cok0Dhagz1RFdNhBIXJy/view
Codex implementa y entrega evidencia; Dilitan revisa. No se invierten esos papeles.

## Correcciones confirmadas

- N15: validacion de hasta cinco adjuntos en una sola consulta y conexion en PostgreSQL; cero consultas para lista vacia. Conserva orden, propietario, borrado y prohibicion de reutilizar un adjunto ya asociado. El acceso individual para descarga no cambia.
- N27: crear, pausar, archivar y reactivar separan las claves de idempotencia por el negocio obtenido del actor autorizado. Dos negocios no comparten respuesta ni conflicto de claves. Los reintentos del mismo negocio conservan replay y rechazo de payload distinto.
- N28: pausar exige active en la misma escritura; si una orden gano antes, devuelve AD_STATUS_INVALID (409), conserva in_order y no audita una pausa exitosa. La implementacion en memoria consulta el registro vigente bajo su bloqueo; PostgreSQL usa update condicional.

## Archivos

- apps/api/app/modules/chat/service.py
- apps/api/app/modules/chat/memory_repository.py
- apps/api/app/modules/chat/postgres_repository.py
- apps/api/app/modules/ads/service.py
- apps/api/app/modules/ads/management.py
- apps/api/app/modules/ads/memory_repository.py
- apps/api/app/modules/ads/postgres_repository.py
- apps/api/tests/test_chat_ad_flow_boundaries.py (18 casos nuevos)
- control_plane/06_API_CONTRACTS/ADS_API.md
- Este reporte, sin otros cambios.

## Evidencia local nueva

Se uso el Python y las dependencias ya instaladas del checkout original; ninguna instalacion.
Ejecutor temporal en memoria: APP_ENV=test, entorno depurado, datos ficticios,
workers desactivados, plugins externos/cache/bytecode desactivados, guardas de
PostgreSQL, Redis, DNS, sockets y procesos. Solo se permite el socketpair interno
de TestClient. Todos los resultados finalizaron con ISOLATION_BLOCKED_COUNT 0.

Comandos pytest (invocados mediante ese ejecutor, no contra servicios):
- pytest apps/api/tests/test_chat_ad_flow_boundaries.py -q -x --tb=short -p no:cacheprovider
  Resultado: 18 passed, 1 warning, 4.93 s.
- pytest apps/api/tests/test_chat_ad_flow_boundaries.py apps/api/tests/test_ads_marketplace.py apps/api/tests/test_chat_disputes.py apps/api/tests/test_credit_hold_idempotency.py -q -x --tb=short -p no:cacheprovider
  Resultado: 140 passed, 1 warning, 25.12 s.
- pytest apps/api/tests -q -x --tb=short -p no:cacheprovider
  Resultado previo al ultimo formato: 1543 passed, 68 skipped, 1 warning, 166.20 s.
  Comprobacion final tras formato: 1543 passed, 68 skipped, 1 warning, 163.15 s; cero conexiones bloqueadas.
- ruff check apps/api/tests/test_chat_ad_flow_boundaries.py --select E,F,I: aprobado.
- ruff format --check apps/api/tests/test_chat_ad_flow_boundaries.py: aprobado.
- git diff --check: aprobado.
- secret-guard --files [los nueve archivos anteriores] --format json: [].

Reproduccion: los casos iniciales fallaron antes del arreglo. Hubo un error del
arnes al nombrar audit_writer, corregido. Un intento de intercalar dos llamadas
HTTP sobre el mismo TestClient se atasco y fue cancelado; se sustituyo solo el
arnes por una llamada al servicio de ordenes en el punto exacto de intercalacion.
Un primer hook interceptaba tambien la transicion de la orden: se acoto a la pausa.
Estos intentos no se cuentan como pruebas aprobadas ni como fallos productivos.
Se agregaron ambas intercalaciones (orden primero / pausa primero), registro
obsoleto, SQL condicional exitoso y rechazado, privacidad de adjuntos y reintentos.

## Limitaciones y gate de integracion

Los 68 skips siguen omitidos; no se presentan como aprobados. El aviso previo
Starlette/httpx permanece. No se probaron DB, Redis, almacenamiento o concurrencia
PostgreSQL reales: la evidencia es API/memoria y SQL con conexion simulada.
No se cambio el resto de avisos de estilo preexistentes en modulos legacy.
No se cambiaron publicacion, precios, creditos, wallets, IP, ni frontend.

IMPORTANTE: la nueva clave por negocio no lee claves legacy. Antes de desplegar,
se necesita una transicion aprobada que preserve los reintentos existentes y evite
versiones mezcladas; TTL por defecto 24 horas. No se borro Redis, no se migro cache,
no se afirma segura una actualizacion en caliente ni autorizada produccion.

## Publicacion y preservacion

Se verifico en solo lectura: Cloudflare nodo-staging sin conexion Git; Railway
nodo-api sin repositorio conectado; GitHub sin webhooks listados; workflows manuales
workflow_dispatch. No se modificaron proveedores ni se inicio despliegue.
Main observado: 74e6d2658dcd545a0d4d4d9aeba8263121a75499.
Checkout original: 6069a75ee2fa6f9b05fdf21ebbfc77039af562c1.
Trabajo aislado en NODO-credit-holds-review, preservando website y laboratorio.
Sin merge, force-push, migraciones, servicios reales, secretos, compras ni cargos cloud.
PR #10 verificado en GitHub como Draft y adjuntado al chat. El reporte inicial
en Drive fue leido y comparado con la copia local antes del push. Se actualiza
esta misma entrega con el enlace del PR y se comprueba por lectura nuevamente.
El commit posterior al funcional agrega solo este reporte; PRESENCIA registra
el HEAD final remoto. Esperar el dictamen de Dilitan sobre este SHA funcional.

