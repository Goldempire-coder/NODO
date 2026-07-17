# CLIENT_ACTIONS_SECURITY_MATRIX.md

## Matriz de acciones sensibles

| Accion cliente | Estado UI propio | Backend manda | Idempotency | Breadcrumb seguro | Datos prohibidos en breadcrumb |
| --- | --- | --- | --- | --- | --- |
| Buscar marketplace | `searchingMarketplace` | Si | N/A | `client_marketplace_search` | monto especifico no requerido |
| Cargar negocios | `loadingMarketplace` | Si | N/A | `client_marketplace_list` | payload de negocio |
| Abrir anuncio | `openingMarketplaceAdId` | Si | N/A | `client_ad_detail_open` | Zelle/wallet completa |
| Crear orden | `creatingOrder` | Si | Si | `client_order_create` | receiver data, telefono, documento |
| Cargar ordenes | `loadingOrders` | Si | N/A | `client_orders_load` | payload de orden |
| Abrir orden | `openingOrderId` | Si | N/A | `client_order_detail_open` | datos receptor completos |
| Extender orden | `extendingOrderId` | Si | Si | `client_order_extend` | motivo libre completo |
| Cancelar orden | `cancellingOrderId` | Si | Si | `client_order_cancel` | motivo libre completo |
| Ver instrucciones | `loadingPaymentInstructions` | Si | N/A | `client_payment_instructions_open` | cuenta/wallet completa |
| Subir comprobante | `uploadingPaymentEvidence` | Si | Si | `client_payment_evidence_upload` | `storage_path`, signed URL |
| Reportar pago | `submittingPaymentReport` | Si | Si | `client_payment_report_submit` | referencia, tx hash, sender completo |
| Abrir chat | `openingChatOrderId` | Si | N/A | `client_chat_open` | mensajes completos |
| Refrescar chat | `refreshingChat` | Si | N/A | `client_chat_refresh` | mensajes completos |
| Subir adjunto chat | `uploadingChatAttachment` | Si | Si | `client_chat_attachment_upload` | `storage_path`, signed URL |
| Enviar chat | `sendingChatMessage` | Si | Si | `client_chat_message_send` | body del mensaje |
| Abrir disputa | `openingOrderDispute` | Si | Si | `client_order_dispute_open` | descripcion completa |
| Crear soporte | `creatingSupportTicket` | Si | Backend | `support_ticket_create` | mensaje completo |
| Responder soporte | `sendingSupportReply` | Si | Backend | `support_reply_send` | mensaje completo |
| Subir adjunto soporte | `uploadingSupportAttachment` | Si | Backend | `support_attachment_upload` | `storage_path`, signed URL |

## Decision

PASS con limites: la Mini App Cliente queda mas limpia y trazable para el carril actual.

No se certifica Admin Web ni flujo cliente-negocio E2E completo en este slice.
