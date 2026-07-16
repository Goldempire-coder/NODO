# UI_CONTRACT.md

## Mini App Cliente

Pantallas:
- Soporte general.
- Soporte por orden.
- Lista de tickets propios.
- Detalle de ticket.
- Mensajes y adjuntos.

Estados:
- loading
- empty
- error
- offline
- retry
- forbidden
- success

## Mini App Negocio

Pantallas:
- Soporte general negocio.
- Soporte por orden.
- Soporte por anuncio.
- Soporte por creditos.
- Lista de tickets propios.
- Detalle de ticket.
- Mensajes y adjuntos.

Reglas:
- Requiere `business_mini_app` allowed.
- No muestra admin.
- No permite acciones criticas fuera del contrato.

## Admin Web

Pantallas:
- Cola de tickets.
- Filtros por status/scope/category/priority/assignee.
- Split view detail.
- Mensajes.
- Asignar.
- Escalar.
- Resolver.
- Cerrar.
- Eventos.
- Adjuntos con signed URL corta.

Reglas:
- Desktop-first.
- Sidebar/top bar existentes.
- Support ve acciones permitidas por RBAC.
- No Telegram MainButton, bottom nav ni Mini App shell.
