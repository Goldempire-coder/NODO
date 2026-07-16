# SURFACE_ARCHITECTURE_MASTER.md

Contrato canonico de superficies para NODO.

## Principio

NODO usa un backend unico compartido, pero las interfaces de usuario se separan por intencion, rol y riesgo:

- Mini App Cliente
- Mini App Negocio
- Panel Admin Web Desktop
- Bot Registro Negocios

El frontend no decide permisos. Cada superficie puede ocultar acciones, pero el backend valida rol, estado, ownership, recurso, superficie y accion.

## Mini App Cliente

Audiencia:

- `remitter` y usuarios cliente autenticados por Telegram.

Incluye:

- Welcome
- Terminos
- Marketplace
- Buscar negocios por monto/metodo
- Lista de negocios activos
- Detalle de negocio
- Crear orden
- Instrucciones de pago
- Reportar pago
- Mis ordenes
- Chat por orden
- Soporte por orden
- Soporte general cliente
- Perfil cliente

No incluye:

- Registro de negocio
- Verificacion de negocio
- Crear anuncios
- Creditos de negocio
- Ordenes entrantes de negocio
- Admin console
- Ajustes manuales
- Metricas admin
- Aprobaciones admin

## Mini App Negocio

Audiencia:

- `business_owner` activo con negocio aprobado y `business_access_links.status = active` asociado a su Telegram/user id.

Incluye:

- Login Telegram
- Dashboard negocio
- Creditos
- Crear/gestionar anuncios
- Ver metodos de pago aprobados como selector/lectura segura
- Ordenes entrantes
- Confirmar pago recibido
- Rechazar reporte de pago
- Marcar entregado
- Chat por orden
- Soporte con NODO
- Perfil negocio
- Historial

No permite:

- Autoaprobarse
- Saltarse verificacion
- Ver otros negocios
- Ver panel admin
- Resolver disputas como admin
- Crear/editar/aprobar/borrar metodos de pago en 14B
- Escribir manualmente `payment_method_id`

Acceso:

- `GET /api/v1/surface/session` con `X-NODO-Surface: business_mini_app` es el gate canonico.
- `GET /api/v1/businesses/me` puede hidratar perfil, pero no autoriza la superficie.
- Bot Registro Negocios no autoriza acceso ni crea negocio activo; admin crea/aprueba/vincula y backend aplica.
- Suspender/bloquear negocio y suspender/bloquear el link de acceso son controles separados.

## Panel Admin Web Desktop

Audiencia:

- `admin`, `super_admin` y `support` segun RBAC.

Incluye:

- Login/admin access seguro
- Dashboard
- Solicitudes del Bot Registro Negocios
- Crear/agregar negocio desde solicitud
- Asociar Telegram ID al negocio
- Buscar/ver usuarios y remitentes
- Controlar estado de usuario segun RBAC
- Ver y administrar `business_access_links`
- Aprobar/rechazar/suspender negocio
- Ver negocios
- Ver ordenes
- Ver disputas
- Resolver disputas
- Ver creditos/compras/manual payments
- Aprobar pagos manuales de creditos
- Ajustes manuales
- Auditoria
- Soporte/tickets
- Staff interno/permisos delegados
- Metricas

Reglas:

- No vive dentro de la Mini App Cliente.
- Debe ser web/desktop y denso, sin bottom nav de cliente.
- Acciones criticas requieren backend RBAC, reason, audit e idempotencia.
- Support es read-only/masked en usuarios y access links.
- Support puede operar tickets de soporte segun contrato 20B: ver cola, responder, asignar, escalar, resolver y cerrar tickets.
- Support no puede resolver disputas formales, cambiar estados de orden, mover creditos, cambiar anuncios ni mutar usuarios/business access desde un ticket.
- En 20C, empleados/colaboradores se gobiernan con `staff_profiles`, `staff_permissions` y `staff_invites`.
- Staff delegado solo opera permisos/scopes activos; `users.role` no basta para granularidad interna.
- Staff Center, Staff Detail e Invite Staff pertenecen solo a Admin Web Desktop.

## Soporte por superficie

Mini App Cliente:

- Puede abrir `client_general` y `client_order`.
- Solo ve tickets propios y tickets ligados a sus ordenes.
- Puede enviar mensajes y adjuntos permitidos mientras el ticket este abierto.

Mini App Negocio:

- Puede abrir `business_general`, `business_order`, `business_ad` y `business_credit`.
- Solo ve tickets del negocio/recurso propio autorizado por backend.
- No obtiene acciones admin ni acceso a otros negocios.

Admin Web:

- Muestra cola desktop de soporte con filtros por status, scope, category, priority y assignee.
- Incluye detalle/split view, respuesta, asignacion, escalamiento, resolucion, cierre, eventos y adjuntos por signed URL corta.
- `support`, `admin` y `super_admin` actuan segun `RBAC_PERMISSION_MATRIX.md`.
- En 20C, staff delegado actua segun `staff_permissions`; staff suspendido/revocado pierde acceso.

Soporte no es disputa:

- Un ticket escalado no crea automaticamente una disputa formal.
- En 20B solo puede vincularse una disputa existente como contexto cuando el actor tiene permiso de verla.
- La disputa formal mantiene su propio contrato, RBAC y efectos sobre orden/creditos/anuncio.

## Bot Registro Negocios

Audiencia:

- Negocios referidos o interesados antes de aprobacion.

Incluye:

- Bienvenida
- Compartir contacto
- Formulario guiado de negocio
- Adjuntos/referencias privadas
- Confirmacion de solicitud recibida
- Creacion de solicitud pendiente para admin
- Notificacion admin

No incluye:

- Crear negocio activo automaticamente
- Publicar anuncios
- Dar acceso al marketplace de negocios
- Prometer aprobacion

## Backend unico

El backend conserva:

- Auth
- RBAC
- Datos
- Audit logs
- Storage privado
- Ordenes
- Negocios
- Creditos
- Soporte
- Jobs

## Prohibiciones globales

- No mezclar admin dentro de Mini App Cliente.
- No poner onboarding/verificacion de negocio dentro de Mini App Cliente.
- No convertir soporte general en disputa sin accion explicita.
- No crear negocio activo desde bot sin revision admin.
- No prometer escrow, fondos garantizados, devolucion, entrega garantizada o custodia de fondos.
## Observability por superficie - slice 24

Cada superficie puede emitir diagnostico operacional solo si esta habilitado por configuracion y siempre con redaccion:

- Mini App Cliente: breadcrumbs de vista, accion, errores visibles y requests API sin payload sensible.
- Mini App Negocio: breadcrumbs equivalentes, mas estado de acceso/surface denials sin exponer datos privados.
- Admin Web: breadcrumbs desktop y errores administrativos sin Telegram runtime ni datos sensibles.
- Bots Telegram: logs/eventos por `telegram_update_id` y `webhook_source`, sin raw update completo ni tokens.
- Backend/workers: logs estructurados con request/correlation/operation ids.

La observabilidad no cambia permisos. Backend sigue siendo autoridad de auth, RBAC, ownership, staff permissions y surface access.
