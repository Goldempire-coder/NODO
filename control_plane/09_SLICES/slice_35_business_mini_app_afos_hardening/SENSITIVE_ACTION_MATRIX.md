# SENSITIVE_ACTION_MATRIX.md

## Estado

Contractual matrix for slice 35 implementation.

## Acciones sensibles

| Accion | Frontend action | Endpoint | PIN desbloqueado | Idempotency-Key | Backend autoridad | Audit/event esperado | Breadcrumb seguro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Agregar Zelle | `zelle_add` | `POST /api/v1/business/payment-methods` | Si | Si | Business service valida negocio, metodo y PIN. | `business_payment_method_self_added` | `zelle_add` |
| Editar Zelle | `zelle_edit` | `PATCH /api/v1/business/payment-methods/{id}` | Si | Si | Business service valida propiedad, activo y duplicado. | `business_payment_method_self_updated` | `zelle_edit` |
| Borrar Zelle | `zelle_delete` | `DELETE /api/v1/business/payment-methods/{id}` | Si | Si | Business service valida propiedad y desactiva. | `business_payment_method_self_deleted` | `zelle_delete` |
| Agregar USDT TRC20 | `usdt_wallet_add` | `POST /api/v1/business/payment-methods` | Si | Si | Business service valida wallet TRC20, negocio y PIN. | `business_payment_method_self_added` | `usdt_wallet_add` |
| Editar USDT TRC20 | `usdt_wallet_edit` | `PATCH /api/v1/business/payment-methods/{id}` | Si | Si | Business service valida propiedad, activo y duplicado. | `business_payment_method_self_updated` | `usdt_wallet_edit` |
| Borrar USDT TRC20 | `usdt_wallet_delete` | `DELETE /api/v1/business/payment-methods/{id}` | Si | Si | Business service valida propiedad y desactiva. | `business_payment_method_self_deleted` | `usdt_wallet_delete` |
| Poner online/offline | `business_availability_update` | `PATCH /api/v1/business/availability` | Si | Si | Business service valida negocio, PIN y status. | `business_accepting_orders_updated` | `business_availability_update` |
| Crear anuncio | `ad_create` | `POST /api/v1/business/ads` | Si | Si | Ads service valida negocio, metodo de cobro, rango y creditos. | `ad_created`, `credits_held` | `ad_create` |
| Editar anuncio | `ad_edit` | `PUT /api/v1/business/ads/{id}` | Si | Si | Ads service valida ownership, rango y metodo de cobro. | `ad_updated` | `ad_edit` |
| Pausar anuncio | `ad_pause` | `POST /api/v1/business/ads/{id}/pause` | Si | Si | Ads service valida ownership y state machine. | `ad_paused` | `ad_pause` |
| Reactivar anuncio | `ad_reactivate` | `POST /api/v1/business/ads/{id}/reactivate` | Si | Si | Ads service valida metodo activo, creditos y estado. | `ad_reactivated`, `credits_held` | `ad_reactivate` |
| Borrar/archivar anuncio | `ad_delete` | `POST /api/v1/business/ads/{id}/archive` | Si | Si | Ads service valida ownership y consumo/liberacion. | `ad_archived`, `credits_consumed` | `ad_delete` |
| Republicar anuncio | `ad_republish` | `POST /api/v1/business/ads/{id}/republish` | Si | Si | Ads service valida credito nuevo y state machine. | `ad_republished`, `credits_held` | `ad_republish` |
| Crear pago Base USDC | `credit_payment_create` | `POST /api/v1/business/credits/base-payment` | Si | Si | Credit service crea compra pendiente. | `onchain_credit_purchase_created` | `credit_payment_create` |
| Enviar tx hash Base USDC | `credit_tx_submit` | `POST /api/v1/business/credits/purchases/{id}/tx-hash` | Si | Si | Credit service/verifier valida chain/token/wallet/monto/tx unica. | `onchain_credit_tx_submitted` o resultado equivalente | `credit_tx_submit` |
| Confirmar pago de orden | `business_order_confirm_payment` | `POST /api/v1/business/orders/{id}/confirm-payment` | Si | Si | Order service valida estado, ownership y consumo atomico. | `payment_confirmed` | `business_order_confirm_payment` |
| Reportar problema con pago | `business_order_dispute_open` | `POST /api/v1/orders/{id}/disputes` | Si | Si | Dispute service valida estado, ownership y razon estructurada; backend abre la disputa atomicamente. | `dispute_opened` | `business_order_dispute_open` |
| Marcar enviado | `business_order_mark_delivered` | `POST /api/v1/business/orders/{id}/mark-delivered` | Si | Si | Order service valida estado y ownership. | `order_delivered` | `business_order_mark_delivered` |
| Enviar chat | `business_chat_send` | Chat order message endpoint | No por defecto | Si | Chat service valida orden y capabilities. | message event | `business_chat_send` |
| Abrir disputa/caso | `business_order_dispute_open` | Dispute endpoint | Si si contrato de disputa lo exige | Si | Backend valida estado y ownership. | dispute event | `business_order_dispute_open` |
| Crear ticket soporte | `business_support_ticket_create` | `POST /api/v1/support/tickets` | No | Si si API lo requiere | Support service valida surface y ownership. | support ticket event | `business_support_ticket_create` |

## Campos prohibidos en breadcrumbs/logs

- PIN.
- Zelle completo o `zelle_account`.
- `account_value`.
- Wallet USDT completa.
- Wallet privada o seed/private key.
- Wallet destino completa en breadcrumbs.
- Tx hash completo.
- Tokens, cookies o Authorization.
- `storage_path`.
- signed URLs.
- Mensajes completos de chat/tickets.
