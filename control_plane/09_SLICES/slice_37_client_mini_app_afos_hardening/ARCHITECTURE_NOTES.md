# ARCHITECTURE_NOTES.md

## Separacion actual

- `useClientWorkspaceModel.ts`: compone la superficie cliente.
- `useClientWorkspaceState.ts`: estado de navegacion, formularios y action state.
- `useClientMarketplaceModel.ts`: busqueda, lista y detalle de anuncios.
- `useRemitterOrdersModel.ts`: crear, listar, abrir, extender y cancelar ordenes.
- `usePaymentReportModel.ts`: instrucciones, evidencia y reporte de pago.
- `useClientChatDisputesModel.ts`: chat, adjuntos y disputa.
- `useSurfaceSupportModel.ts`: soporte compartido cliente/negocio.
- `actionTelemetry.ts`: breadcrumbs y duracion de acciones.

## Reglas de arquitectura

- Un hook de cliente no debe importar desde `business-mini-app`.
- Un hook de negocio no debe importar desde `screens/client`.
- Una pantalla no debe construir payloads financieros complejos; debe delegar al hook/API.
- Una accion puntual no debe usar `busy` global si puede usar estado propio.
- Una accion con datos sensibles debe registrar solo nombre de accion, pantalla, duracion y codigo de error seguro.

## Pendientes para otro slice

- Medicion Playwright de transiciones reales en Mini App cliente.
- Prueba manual Telegram de cliente contra negocio con orden real.
- Auditoria AFOS de Admin Web.
