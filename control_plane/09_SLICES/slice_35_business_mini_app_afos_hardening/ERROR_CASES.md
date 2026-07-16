# ERROR_CASES.md

## Errores que deben tener UX clara

Access/PIN:

- `BUSINESS_PIN_NOT_SET`
- `BUSINESS_PIN_REQUIRED`
- `BUSINESS_PIN_INVALID`
- `BUSINESS_PIN_LOCKED`
- `BUSINESS_NOT_APPROVED`
- `FORBIDDEN`

Metodos de cobro:

- `PAYMENT_METHOD_NOT_FOUND`
- `PAYMENT_METHOD_INVALID`
- `PAYMENT_METHOD_DUPLICATE`
- `PAYMENT_METHOD_LIMIT_REACHED`
- `PAYMENT_METHOD_NOT_APPROVED`

Ads:

- `AD_NOT_FOUND`
- `AD_NOT_AVAILABLE`
- `AD_STATUS_INVALID`
- `AD_LIMIT_NOT_ALLOWED`
- `AD_OVERLAP_NOT_ALLOWED`
- `INSUFFICIENT_CREDITS`
- `INVALID_PAYMENT_METHOD`
- `INVALID_DELIVERY_METHOD`

Credits:

- `ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED`
- `CREDIT_PACKAGE_NOT_FOUND`
- `BASE_USDC_TX_INVALID`
- `BASE_USDC_TX_NOT_FOUND`
- `BASE_USDC_TX_AMOUNT_MISMATCH`
- `BASE_USDC_TX_DESTINATION_MISMATCH`
- `BASE_USDC_TX_PENDING_CONFIRMATIONS`

Orders:

- `ORDER_NOT_FOUND`
- `ORDER_STATUS_INVALID`
- `BUSINESS_OFFLINE`
- `PAYMENT_REPORT_REQUIRED`
- `PAYMENT_REPORT_ALREADY_EXISTS`

Transport/UI:

- network timeout;
- 401/refresh failed;
- offline client;
- API route unavailable;
- load failed.

## Reglas

- El boton no debe "titilar" sin resultado.
- Cada error debe dejar mensaje accionable.
- Si requiere PIN, debe navegar a PIN y volver a la accion.
- Si falla por metodo de cobro borrado, debe ofrecer editar anuncio o crear un metodo activo.
- Si falla por wallet Base no configurada, debe decir que la compra no esta disponible todavia.
- Si falla por transporte, debe permitir reintentar sin duplicar accion sensible.
