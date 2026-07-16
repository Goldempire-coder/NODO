# DATA_CONTRACT.md

## Principio

Este slice no debe crear datos nuevos salvo evidencia o matriz de control. Las entidades financieras y operativas ya existentes deben conservar sus invariantes.

## Entidades relevantes

- `businesses`
- `business_access_links`
- `business_payment_methods`
- `ads`
- `credit_wallets`
- `credits_ledger`
- `credit_purchases`
- `credit_purchase_onchain_payments`
- `orders`
- `order_state_events`
- `payment_reports`
- `messages`
- `message_attachments`
- `support_tickets`
- `audit_logs`

## Reglas de datos

- No crear migracion sin bug o contrato explicito.
- No eliminar columnas.
- No cambiar significado de estados.
- No cambiar formato de `public_order_code`.
- No exponer `account_value` completo fuera del contexto propio del negocio.
- No guardar PIN en claro.
- No guardar wallet privada.
- No guardar seed phrase.
- No duplicar creditos por retry.
- No permitir saldos negativos.
- No romper relacion anuncio -> metodo de cobro -> negocio.
- No romper relacion orden -> anuncio -> negocio -> cliente.

## Si se requiere migracion

El builder debe:

- justificar por que es necesaria;
- crear up/down;
- agregar test;
- explicar rollback;
- no ejecutarla contra produccion.

## Evidencia

- tests de integridad;
- tests de idempotencia;
- tests de ownership;
- scan de datos sensibles;
- diff de migraciones si existen.
