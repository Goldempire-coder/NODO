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
- Ver ordenes.
- Ver disputas.
- Resolver disputas.
- Ver creditos/compras/manual payments.
- Aprobar pagos manuales de creditos.
- Ajustes manuales.
- Auditoria.
- Soporte/tickets.
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
- No mostrar `storage_path`, `account_value`, tokens, secretos, signed URLs persistidas ni evidencia privada completa.
- Documentos/evidencias completas solo mediante endpoint autorizado de signed URL corta y audit.

## No incluye

- Mini App Cliente.
- Mini App Negocio.
- Telegram MainButton como navegacion primaria.
- Telegram bottom nav.
- Telegram Mini App shell.
- `@telegram-apps/telegram-ui` como sistema obligatorio.
- `themeParams` como fuente de tema.
- Claims de escrow, fondos garantizados o garantia de entrega.
