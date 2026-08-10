# ERROR_CASES.md

Errores esperados para `slice_06_business_order_ops`.

## Errores comunes

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `VALIDATION_ERROR`
- `RATE_LIMITED`
- `ORDER_NOT_FOUND`
- `ORDER_NOT_OWNED`
- `ORDER_STATUS_INVALID`
- `IDEMPOTENCY_KEY_REQUIRED`
- `IDEMPOTENCY_CONFLICT`
- `IDEMPOTENCY_PAYLOAD_MISMATCH`

## Confirm-payment

- `PAYMENT_REPORT_NOT_FOUND`
- `PAYMENT_CONFIRMATION_NOT_ALLOWED`
- `CREDIT_HOLD_NOT_FOUND`
- `CREDIT_ALREADY_CONSUMED`

## Reject-payment-report legacy

- `PAYMENT_REJECTION_NOT_ALLOWED`

## Reportar problema con pago

- `PAYMENT_REPORT_NOT_FOUND`
- `DISPUTE_NOT_ALLOWED`
- `DISPUTE_REASON_REQUIRED`

## Mark-delivered

- `DELIVERY_NOT_ALLOWED`

## Reglas

- Usar `06_API_CONTRACTS/ERROR_CONTRACT.md`.
- No exponer stack traces, SQL, secretos, tokens, instrucciones completas, `account_value` ni storage keys privados.
- Errores de permisos no deben filtrar existencia de recursos ajenos.
- UI debe mapear cada error esperado a un estado seguro.
