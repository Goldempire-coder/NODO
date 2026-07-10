# ADMIN_WEB_ARCHITECTURE.md

## Objetivo

El panel admin debe ser web/desktop profesional, separado de la Mini App Cliente.

## Reglas

- No usar bottom nav de cliente.
- No vivir en el flujo de Mini App Cliente.
- Debe tener layout denso para tablas, filtros, colas y detalles.
- Debe ser desktop-first y responsive minimo para laptop/tablet; no mobile-first Telegram.
- Debe usar sidebar o navegacion lateral, top bar administrativa y paneles de detalle/split view.
- No debe depender de `@telegram-apps/telegram-ui`, `themeParams`, Telegram MainButton ni shell Mini App.
- Debe consumir solo endpoints `/api/v1/admin/*` y contratos admin relacionados.
- Toda mutacion critica requiere reason, audit e idempotencia.

## Roles

- `admin`: opera segun RBAC.
- `super_admin`: opera y puede roles criticos si contrato lo permite.
- `support`: lectura/respuesta/escalamiento solo segun RBAC; no acciones criticas no autorizadas.

## Seguridad

- Auth/session segura.
- La superficie debe identificarse como `admin_web` cuando el backend lo requiera.
- Backend RBAC obligatorio.
- No frontend-only permissions.
- No exponer `storage_path`, `account_value`, tokens, secretos ni evidencia privada completa.
