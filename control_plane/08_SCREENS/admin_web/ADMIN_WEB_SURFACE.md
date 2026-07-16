# ADMIN_WEB_SURFACE.md

## Owner

Panel Admin Web Desktop.

## Incluye

- Login/admin access seguro.
- Dashboard.
- Solicitudes del Bot Registro Negocios.
- Crear/agregar negocio desde solicitud.
- Asociar Telegram ID al negocio.
- Aprobar/rechazar/suspender negocio.
- Ver negocios.
- Ver usuarios/remitentes.
- Controlar estado de usuarios segun RBAC.
- Ver y administrar vinculos `business_access_links`.
- Ver ordenes.
- Ver disputas.
- Resolver disputas.
- Ver creditos/compras/manual payments.
- Aprobar pagos manuales de creditos.
- Ajustes manuales.
- Auditoria.
- Soporte/tickets.
- Staff interno y permisos delegados.
- Metricas.

## Layout obligatorio

- Desktop-first.
- Sidebar o navegacion lateral persistente.
- Top bar administrativa con usuario, rol y estado de sesion.
- Area principal con tablas densas pero legibles.
- Filtros, busqueda y cursor pagination en listas.
- Panel de detalle o split view para revision de recursos.
- Estados loading, empty, error, forbidden y offline.
- Responsive minimo para laptop/tablet; no es mobile-first.

## Seguridad UI

- El frontend no decide permisos; backend RBAC manda.
- Acciones sensibles muestran confirmacion y reason obligatorio.
- Support ve controles read-only salvo contrato explicito.
- Support ve usuarios/access links solo masked/read-only.
- Excepcion 20B: Support puede operar tickets de soporte desde Admin Web segun RBAC:
  responder, asignar, escalar, resolver, cerrar y abrir adjuntos por signed URL corta.
- Esa excepcion no autoriza mutaciones de ordenes, creditos, anuncios, disputas formales, usuarios ni `business_access_links`.

## Soporte 20B

Pantalla canonica:

- `AW-20_SUPPORT_TICKET_CENTER.md`

Layout:

- Sidebar Admin Web.
- Top bar administrativa.
- Cola con tabla densa, filtros por status/scope/category/priority/assignee y busqueda.
- Paginacion/cursor.
- Split view de detalle con mensajes, eventos, adjuntos y acciones permitidas.
- Estados loading/empty/error/forbidden.
- Adjuntos se abren solo con signed URL corta y audit.
- Mutaciones de usuario/access link requieren reason, idempotencia y audit.
- No mostrar `storage_path`, `account_value`, tokens, secretos, signed URLs persistidas ni evidencia privada completa.
- Documentos/evidencias completas solo mediante endpoint autorizado de signed URL corta y audit.

## Staff interno 20C

Pantallas canonicas:

- `AW-21_STAFF_CENTER.md`
- `AW-22_STAFF_DETAIL.md`
- `AW-23_STAFF_INVITE.md`

Layout:

- Sidebar Admin Web.
- Top bar administrativa.
- Tabla densa de staff con filtros por status, role y permiso.
- Detalle split view con matriz de permisos, scopes, actividad y tickets asignados.
- Formulario de invitacion con reason obligatorio y preview de permisos.

Seguridad:

- Solo `super_admin` muta staff/permisos.
- `admin` puede leer staff si RBAC lo permite.
- `support` y staff delegado no administran staff.
- Mutaciones requieren `Idempotency-Key`, reason, backend RBAC y audit.
- No exponer tokens, secretos, `storage_path`, `account_value`, signed URLs persistidas ni datos privados completos.
- Staff delegado no puede ejecutar acciones criticas de usuarios, negocios, creditos, disputas, ordenes, anuncios ni access links.

## No incluye

- Mini App Cliente.
- Mini App Negocio.
- Telegram MainButton como navegacion primaria.
- Telegram bottom nav.
- Telegram Mini App shell.
- `@telegram-apps/telegram-ui` como sistema obligatorio.
- `themeParams` como fuente de tema.
- Claims de escrow, fondos garantizados o garantia de entrega.
## Observability / Diagnostics - slice 24

Admin Web may include a desktop diagnostics view only after slice 24 build approval.

Capabilities:

- search by request, correlation, operation, session and resource ids;
- view redacted event timeline;
- filter by surface, status, error code and time window;
- export redacted diagnostic evidence with audit.

RBAC:

- `super_admin`: full redacted operational search.
- `admin`: operational search under admin scope.
- `support`: limited to support-visible tickets/sessions and masked values.
- staff: requires granular `view_observability_events` permission.

Prohibited:

- raw payloads;
- full messages;
- documents;
- signed URLs;
- tokens/secrets;
- `storage_path`;
- `account_value`;
- full tx hash.
