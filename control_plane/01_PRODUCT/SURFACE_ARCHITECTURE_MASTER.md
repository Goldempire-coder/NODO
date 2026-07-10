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
- Metricas

Reglas:

- No vive dentro de la Mini App Cliente.
- Debe ser web/desktop y denso, sin bottom nav de cliente.
- Acciones criticas requieren backend RBAC, reason, audit e idempotencia.

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
