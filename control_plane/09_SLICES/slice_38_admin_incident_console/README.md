# slice_38_admin_incident_console

Estado contractual: `READY_FOR_OWNER_REVIEW`.

## Objetivo

Agregar un Centro de Incidentes al Admin Web para responder rapido cuando NODO falle o se degrade.

## Alcance

- Resumen operativo calculado desde fuentes existentes.
- Salud de dependencias desde readiness.
- Modo emergencia visible.
- Colas operativas del dashboard.
- Jobs recientes fallidos.
- Notificaciones con problemas.
- Auditoria reciente sin metadata sensible.
- Acciones recomendadas para el operador.

## No Alcance

- No reemplaza logs de Railway, Supabase, Redis ni proveedores.
- No crea una tabla nueva de logs.
- No ejecuta recuperacion automatica.
- No toca reglas de dinero, ordenes, creditos, Zelle ni Base USDC.
- No hace deploy ni declara `READY_FOR_REAL_USE`.

## Criterio de salida

- Admin/support pueden abrir `/api/v1/admin/incident-console`.
- Roles no admin no pueden abrirlo.
- La respuesta no expone `account_value`, `storage_path`, tokens, secretos ni payloads completos.
- Admin Web muestra una vista `Incidentes`.
- Tests backend y build web pasan.
