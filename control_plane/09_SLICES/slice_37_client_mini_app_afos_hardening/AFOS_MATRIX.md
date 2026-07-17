# AFOS_MATRIX.md

## Estado

Slice 37 hardening matrix: `READY_FOR_OWNER_REVIEW`.

## Componentes revisados

| Area | Frontend owner | Backend authority | Estado | Evidencia |
| --- | --- | --- | --- | --- |
| Surface cliente | `useClientWorkspaceModel`, `ClientWorkspaceShell` | auth/session backend | PASS | `X-NODO-Surface` y token auth viven en API client/session. |
| Marketplace | `useClientMarketplaceModel`, `ClientMarketplaceScreens` | ads marketplace backend | PASS | Frontend filtra y muestra; backend decide anuncio visible, negocio online y limites. |
| Crear orden | `useRemitterOrdersModel`, `ClientOrderScreens` | order creation backend | PASS | Backend valida ad, negocio, monto, ownership, idempotency y mueve anuncio a `in_order`. |
| Reportar pago | `usePaymentReportModel`, `ClientPaymentScreens` | payment reporting backend | PASS | Backend valida estado, evidencia privada, Zelle/USDT y `pending_payment_report_id`. |
| Chat/disputa | `useClientChatDisputesModel`, `ClientScreens` | chat/dispute backend | PASS | Backend valida ownership y estados; frontend no resuelve disputas. |
| Soporte | `useSurfaceSupportModel`, `ClientSupportScreen` | support backend | PASS | Ticket y adjuntos son backend-authoritative. |
| Observabilidad | `actionTelemetry.ts`, `clientTelemetry.ts` | observability ingest backend | PASS | Breadcrumbs de acciones sin valores sensibles. |
| Admin Web | n/a | n/a | OUT_OF_SCOPE | Proximo carril despues de cliente. |

## Hallazgos cerrados

| ID | Riesgo | Cambio |
| --- | --- | --- |
| AFOS-CLIENT-001 | Acciones sensibles dependian del `busy` global y podian parecer congeladas. | Estados por accion para ordenes, pagos, chat, disputa, marketplace y soporte. |
| AFOS-CLIENT-002 | Helper de acciones vivia dentro de `business-mini-app`. | Helper compartido en `apps/web/src/hooks/actionTelemetry.ts`. |
| AFOS-CLIENT-003 | Falta de breadcrumbs seguros para acciones criticas del cliente. | `client_order_create`, `client_payment_report_submit`, `client_chat_message_send`, `client_order_dispute_open`, soporte y marketplace. |
| AFOS-CLIENT-004 | Cache de ordenes podia quedar vieja tras crear, extender o cancelar. | La lista local se actualiza al recibir la orden actualizada del backend. |

## Reglas AFOS aplicadas

- El backend autoriza y valida cada accion sensible.
- El frontend no decide dinero, ownership, estado final, creditos ni disponibilidad del negocio.
- Los logs/breadcrumbs no pueden incluir token, PIN, wallet completa, Zelle completo, tx hash completo, `storage_path`, signed URLs ni `account_value`.
- Los botones deben decir que accion esta corriendo y no bloquear pantallas no relacionadas.
- Admin Web queda separado hasta su propio slice.
