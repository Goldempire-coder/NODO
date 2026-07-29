# Slice 47A - Operability Observability Base

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Convertir NODO en un sistema observable de forma basica y segura. El operador
debe poder responder: donde se trabo el flujo, que version estaba corriendo,
que request fallo y que superficie lo produjo: cliente, negocio, admin,
backend, Telegram, DB, Redis, storage o red.

Este slice no busca agregar dashboards bonitos primero. Busca que cada flujo
critico deje senales consistentes, correlacionables y sin datos sensibles.

La prioridad es medir salud real del usuario, no solo salud tecnica. Si el
servidor responde pero el cliente no puede crear una orden, abrir soporte,
ver negocios disponibles o terminar un flujo, el sistema debe marcarlo como
degradacion operativa.

## Problema Que Cubre

Hoy el sistema tiene health, ready, version, audit y algunos breadcrumbs, pero
la observabilidad aun no esta cerrada como contrato transversal. Cuando algo
falla, soporte puede quedar adivinando si el problema nacio en la mini app, API,
proveedor, storage, Redis o una accion de usuario.

## Resultado Esperado

- Inventario de eventos y senales actuales por superficie.
- Contrato unico de `request_id`, `correlation_id`, version y superficie.
- Logs estructurados con allowlist, sin cuerpos privados.
- Breadcrumbs seguros para acciones criticas de cliente, negocio y admin.
- Metricas de salud por flujo: creacion de orden, busqueda de negocios,
  soporte, intake, creditos, disponibilidad del negocio y notificaciones.
- Metricas de costo por flujo: usuario activo, negocio activo, orden, soporte,
  hora de Dashboard, dolar generado y flujo fallido.
- Golden signals por superficie: trafico, errores, latencia p95/p99 y
  saturacion visible.
- Health checks profundos para dependencias criticas: DB, Redis, storage,
  Telegram y API externa cuando aplique.
- Mapa de flujo para orden, soporte, intake, creditos y notificaciones.
- Reporte de brechas y plan de instrumentacion minima.

## Dependencias

- 20B soporte.
- 24 observabilidad/debuggability.
- 35/37 hardening de mini apps.
- 46A-46D investigacion y soporte admin.

## No Construir Todavia

- No agregar proveedor nuevo.
- No agregar session replay de video.
- No guardar cuerpos completos de chat o soporte.
- No guardar wallets, bancos, PIN, tokens, documentos ni datos privados.
- No crear alertas automaticas todavia; eso vive en 47B.
- No crear jobs ni reconciliacion; eso vive en 47C.
- No hacer deploy ni tocar produccion.
