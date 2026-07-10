# UI_CONTRACT.md

Pantallas canonicas afectadas:

- B-04_BUSINESS_DASHBOARD: dashboard de creditos/resumen.
- B-05_BUY_CREDITS: paquetes y checkout/manual payment.
- B-06_CREDIT_PAYMENT_PENDING: comprobante manual y estado pending review.
- B-07_MY_CREDITS_LEDGER: wallet y ledger.
- B-15_REFERRAL_PROGRAM: codigo, eventos y cap.
- A-04_PENDING_CREDIT_PAYMENTS: lista admin de compras pendientes.
- A-05_CREDIT_PAYMENT_DETAIL: detalle admin approve/reject.
- A-13_MANUAL_ADJUSTMENTS: ajuste admin de creditos.

Nombres no canonicos no deben crearse como pantallas nuevas:

- B-04_CREDITS_DASHBOARD
- B-06_PAYMENT_PROOF
- B-07_REFERRALS
- A-04_CREDIT_PAYMENTS

UI rules:

- Telegram Mini App mobile-first.
- Usar Telegram UI kit donde aplique.
- Respetar themeParams, safe areas y MainButton.
- Incluir loading, empty, error, offline, forbidden y success states.
- No landing.
- No UI generica.
- No mostrar `storage_path`.
- No mostrar Stripe secrets.
- Manual references, tx hash y proof metadata se muestran masked salvo vista admin autorizada.
- Copy debe decir que los creditos son publicitarios/listing credits, no fondos de clientes.
- Copy debe decir que NODO no recibe, retiene, transfiere ni garantiza fondos de remesas.

Copy prohibido:

- escrow
- fondos protegidos
- garantia de entrega
- NODO recibio tu dinero
- pago garantizado
- transaccion asegurada
